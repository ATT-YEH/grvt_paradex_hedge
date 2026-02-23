"""
專為對沖機器人優化的 GRVT 客戶端 (grvthedge.py)
"""
import asyncio
from decimal import Decimal
from typing import List
from .grvt import GrvtClient, OrderInfo


class GrvtHedgeClient(GrvtClient):
    """繼承原始 GrvtClient 並優化對沖專用方法"""

    async def cancel_all_orders(self, contract_id: str):
        """
        修正原本不存在的方法：獲取所有掛單並逐一撤銷
        """
        active_orders = await self.get_active_orders(contract_id)
        if not active_orders:
            return True

        tasks = [self.cancel_order(order.order_id) for order in active_orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return all(not isinstance(r, Exception) for r in results)

    async def get_active_orders(self, contract_id: str) -> List[OrderInfo]:
        """
        確保回傳 OrderInfo 物件清單，供 Chase Mode 遍歷使用
        """
        try:
            # 調用父類別的 REST 實作
            orders = await super().get_active_orders(contract_id)
            return orders if isinstance(orders, list) else []
        except Exception as e:
            self.logger.log(f"獲取掛單失敗: {e}", "ERROR")
            return []

    async def get_account_positions(self) -> Decimal:
        """
        獲取當前合約的實體淨持倉 (Decimal)
        """
        try:
            # 確保使用 rest_client 進行 REST 輪詢
            pos = await super().get_account_positions()
            return Decimal(str(pos))
        except Exception:
            return Decimal("0")