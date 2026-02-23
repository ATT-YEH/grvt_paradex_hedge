import requests
import time
from decimal import Decimal

class TelegramReporter:
    def __init__(self, token: str, chat_id: str, enabled: bool = False):
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled
        self.total_wear_and_tear = Decimal('0')

    def send_round_report(self, ticker: str, round_num: int, grvt_pnl: Decimal, pdex_pnl: Decimal, total_volume: Decimal):
        if not self.enabled or not self.token or not self.chat_id:
            return

        round_wear = grvt_pnl + pdex_pnl
        self.total_wear_and_tear += round_wear

        # 依照你要求的格式建構訊息
        message = (
            f"🔹 {ticker} 第 {round_num} 輪已結束\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 GRVT 平倉盈虧: {grvt_pnl:+.4f}\n"
            f"💰 Paradex 平倉盈虧: {pdex_pnl:+.4f}\n"
            f"--------------------------\n"
            f"📉 此輪磨損(兩邊盈虧加總): {round_wear:+.4f}\n"
            f"📊 目前總磨損: {self.total_wear_and_tear:+.4f}\n"
            f"📈 目前總交易量: {total_volume:.2f} U"
        )

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": message}, timeout=5)
        except Exception as e:
            print(f"Telegram 發送失敗: {e}")