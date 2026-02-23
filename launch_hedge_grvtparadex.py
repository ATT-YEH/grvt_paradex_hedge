import argparse
import asyncio
from decimal import Decimal
from hedge.hedge_mode_grvtparadex import HedgeBot

async def main():
    parser = argparse.ArgumentParser(description="Launch GRVT/Paradex Hedge Bot")
    parser.add_argument("--ticker", type=str, required=True, help="Market ticker (e.g., BTC)")
    parser.add_argument("--size", type=str, required=True, help="Order quantity")
    parser.add_argument("--iter", type=int, default=10, help="Number of iterations")
    parser.add_argument("--fill-timeout", type=int, default=10, help="Fill timeout")
    parser.add_argument("--start-side", type=str, default="buy", help="Initial side (buy/sell)")
    # 新增此參數以接收指令列的輸入，預設 60 秒
    parser.add_argument("--holding-time", type=int, default=60, help="Holding time in seconds")

    args = parser.parse_args()

    print(f"Starting GRVT/Paradex Hedge Mode: {args.ticker} Size: {args.size}, Side: {args.start_side}, Holding: {args.holding_time}s")
    print("-" * 50)

    # 確保這裡的參數名稱與 HedgeBot.__init__ 完全一致
    bot = HedgeBot(
        ticker=args.ticker,
        order_quantity=Decimal(args.size),
        fill_timeout=args.fill_timeout,
        iterations=args.iter,
        start_side=args.start_side,
        holding_time=args.holding_time  # 傳遞持倉時間
    )

    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping bot...")