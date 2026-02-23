import asyncio
import logging
import os
import sys
import time # 補齊 time 模組
from decimal import Decimal
from dotenv import load_dotenv

# --- 導入模組 ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 🚨 自動尋找當前目錄下的 .env
load_dotenv(override=True)

from exchanges.grvthedge import GrvtHedgeClient as GrvtClient
from exchanges.interceptor import AuthInterceptor
from exchanges.account import ParadexAccount
from reporter import TelegramReporter

# --- 策略常數 ---
POLLING_INTERVAL = 1.0
CHASE_INTERVAL = 2.0


class HedgeBot:
    def __init__(self, ticker: str, order_quantity: Decimal, fill_timeout: int = 10, iterations: int = 20,
                 start_side: str = 'buy', holding_time: int = 60):
        self.ticker = ticker.upper()
        self.paradex_ticker = f"{self.ticker}-USD-PERP" if "-" not in self.ticker else self.ticker
        self.grvt_ticker = self.ticker.split("-")[0]

        self.order_quantity = order_quantity
        self.iterations = iterations
        self.start_side = start_side
        self.current_side = start_side
        self.holding_time = holding_time

        # 盈虧統計與交易量變數
        self.round_grvt_cash_flow = Decimal('0')
        self.round_pdex_cash_flow = Decimal('0')
        self.total_volume_u = Decimal('0')  # 新增：累計總交易量

        # Telegram 配置
        self.tg_enabled = os.getenv("TG_ENABLED", "False").lower() == "true"
        self.tg_reporter = TelegramReporter(
            token=os.getenv("TG_BOT_TOKEN"),
            chat_id=os.getenv("TG_CHAT_ID"),
            enabled=self.tg_enabled
        )

        self.grvt_position = Decimal('0')
        self.paradex_position = Decimal('0')
        self.stop_flag = False
        self._setup_logger()

        self.grvt_client = None
        self.paradex_account = None
        self.grvt_contract_id = None

    def _setup_logger(self):
        self.logger = logging.getLogger(f"HedgeBot_{self.ticker}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

    def initialize_clients(self):
        AuthInterceptor.install(enabled=True, token_usage="interactive")
        grvt_config = type('Config', (), {
            'ticker': self.grvt_ticker, 'quantity': self.order_quantity, 'tick_size': Decimal('0.01'),
            'contract_id': None
        })
        self.grvt_client = GrvtClient(grvt_config)
        self.paradex_account = ParadexAccount(
            name="SingleHedgeAcc",
            l2_private_key=os.getenv("PARADEX_L2_PRIVATE_KEY"),
            l2_address=os.getenv("PARADEX_L2_ADDRESS")
        )

    async def paradex_hedge_action(self, side: str, qty: Decimal, is_close: bool = False):
        try:
            bid, ask = await self.grvt_client.fetch_bbo_prices(self.grvt_contract_id)
            fill_price = ask if side.upper() == "BUY" else bid

            self.logger.info(f"🚀 Paradex 發送: {side.upper()} {qty} (預估均價: {fill_price})")
            result = await asyncio.to_thread(
                self.paradex_account.place_market_order,
                market=self.paradex_ticker, side=side.upper(), size=qty, reduce_only=is_close
            )
            if result:
                val = qty * fill_price
                if side.upper() == "BUY":
                    self.round_pdex_cash_flow -= val
                else:
                    self.round_pdex_cash_flow += val

                self.paradex_position += qty if side.upper() == "BUY" else -qty
                if is_close: self.paradex_position = Decimal('0')
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Paradex 動作失敗: {e}")
            return False

    async def trading_loop(self):
        self.grvt_contract_id, _ = await self.grvt_client.get_contract_attributes()
        await self.grvt_client.connect()

        for i in range(1, self.iterations + 1):
            if self.stop_flag: break

            self.round_grvt_cash_flow = Decimal('0')
            self.round_pdex_cash_flow = Decimal('0')
            prev_grvt_pos = await self.grvt_client.get_account_positions()

            side = self.start_side if i == 1 else ('buy' if self.current_side == 'sell' else 'sell')
            self.current_side = side
            self.logger.info(f"\n🔄 --- 第 {i} / {self.iterations} 輪開始 ({side.upper()}) ---")

            # 1. GRVT 開倉階段
            last_target_price = Decimal('0')
            while not self.stop_flag:
                current_pos = await self.grvt_client.get_account_positions()
                filled_qty = current_pos - prev_grvt_pos
                if filled_qty != 0:
                    trade_val = abs(filled_qty) * last_target_price
                    self.round_grvt_cash_flow -= (filled_qty * last_target_price)
                    self.total_volume_u += trade_val # 累加開倉交易量
                    prev_grvt_pos = current_pos

                if abs(current_pos) >= self.order_quantity:
                    self.logger.info(f"🎯 [開倉成功] GRVT 持倉: {current_pos}")
                    pdex_side = 'sell' if current_pos > 0 else 'buy'
                    if await self.paradex_hedge_action(pdex_side, abs(current_pos)):
                        break

                bid, ask = await self.grvt_client.fetch_bbo_prices(self.grvt_contract_id)
                last_target_price = bid if side == 'buy' else ask
                await self.grvt_client.cancel_all_orders(self.grvt_contract_id)
                await self.grvt_client.place_post_only_order(self.grvt_contract_id,
                                                             (self.order_quantity - abs(current_pos)),
                                                             last_target_price, side)
                await asyncio.sleep(CHASE_INTERVAL)

            # 2. 持倉等待
            self.logger.info(f"⏳ 持倉中 ({self.holding_time}s)...")
            await asyncio.sleep(self.holding_time)

            # 3. GRVT 平倉階段 (處理 0.8+0.2 分批成交)
            while not self.stop_flag:
                current_pos = await self.grvt_client.get_account_positions()
                filled_qty = current_pos - prev_grvt_pos
                if filled_qty != 0:
                    trade_val = abs(filled_qty) * last_target_price
                    self.round_grvt_cash_flow -= (filled_qty * last_target_price)
                    self.total_volume_u += trade_val # 累加平倉交易量
                    prev_grvt_pos = current_pos

                if abs(current_pos) < Decimal('0.00000001'):
                    self.logger.info("✅ GRVT 倉位已清空")
                    pdex_close_side = 'buy' if self.paradex_position < 0 else 'sell'
                    await self.paradex_hedge_action(pdex_close_side, abs(self.paradex_position), is_close=True)
                    break

                bid, ask = await self.grvt_client.fetch_bbo_prices(self.grvt_contract_id)
                close_side = 'sell' if current_pos > 0 else 'buy'
                last_target_price = ask if close_side == 'sell' else bid
                await self.grvt_client.cancel_all_orders(self.grvt_contract_id)
                await self.grvt_client.place_post_only_order(self.grvt_contract_id, abs(current_pos), last_target_price,
                                                             close_side)
                await asyncio.sleep(CHASE_INTERVAL)

            # 🏁 發送 Telegram 報告 (包含 Ticker 與 總交易量)
            self.tg_reporter.send_round_report(
                ticker=self.ticker,
                round_num=i,
                grvt_pnl=self.round_grvt_cash_flow,
                pdex_pnl=self.round_pdex_cash_flow,
                total_volume=self.total_volume_u
            )
            await asyncio.sleep(5)

    async def run(self):
        self.initialize_clients()
        await self.trading_loop()