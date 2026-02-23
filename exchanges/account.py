"""
Paradex 帳戶類別 - 強化導入相容性版本 (適配 SDK 0.5.4+)
"""

import time
from decimal import Decimal
from typing import Optional, List
from functools import wraps


# 1. 基礎導入
from paradex_py import ParadexSubkey

# 2. 強化導入 Order 相關類別 (針對 0.5.4+ 重構進行自動偵測)
try:
    # 優先嘗試從頂層導入 (根據你的 dir(paradex_py) 測試結果)
    from paradex_py import Order, OrderSide, OrderType
    print("DEBUG: Order classes imported from top-level 'paradex_py'")
except ImportError:
    try:
        # 嘗試 SDK 0.5.x 的 models 路徑
        from paradex_py.api.models import Order, OrderSide, OrderType
        print("DEBUG: Order classes imported from 'paradex_py.api.models'")
    except ImportError:
        # 最後嘗試舊版路徑
        from paradex_py.common.order import Order, OrderSide, OrderType
        print("DEBUG: Order classes imported from 'paradex_py.common.order'")

# 3. 內部工具導入
from exchanges.time_utils import now_timestamp, now_utc8

def retry_on_error(max_retries: int = 3, delay: float = 2.0, backoff: float = 2.0):
    """重試裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    retryable = any(x in error_msg for x in [
                        'temporary failure', 'name resolution', 'connection',
                        'timeout', 'reset by peer', 'broken pipe', 'network', 'ssl', 'eof',
                    ])
                    if not retryable:
                        raise
                    if attempt < max_retries - 1:
                        print(f"[重試] {func.__name__} 失敗({attempt+1}/{max_retries}): {e}, {current_delay}s後重試...")
                        time.sleep(current_delay)
                        current_delay *= backoff
            raise last_error
        return wrapper
    return decorator

class ParadexAccount:
    def __init__(self, name: str, l2_private_key: str, l2_address: str, env: str = "prod", cache_ttl: float = 1.0):
        self.name = name
        self.l2_address = l2_address
        # 初始化 ParadexSubkey
        self.client = ParadexSubkey(env=env, l2_private_key=l2_private_key, l2_address=l2_address)
        self._position_cache = None
        self._position_cache_time = 0
        self._position_cache_ttl = cache_ttl

    @retry_on_error(max_retries=3, delay=2.0)
    def get_account_summary(self):
        return self.client.api_client.fetch_account_summary()

    def get_equity(self) -> Decimal:
        try:
            s = self.get_account_summary()
            if s:
                # 兼容不同版本的欄位名稱
                val = getattr(s, 'account_value', None) or getattr(s, 'equity', 0)
                return Decimal(str(val))
            return Decimal("0")
        except:
            return Decimal("0")

    @retry_on_error(max_retries=3, delay=2.0)
    def get_positions(self) -> List:
        now = now_timestamp()
        if self._position_cache is not None and (now - self._position_cache_time) < self._position_cache_ttl:
            return self._position_cache
        try:
            r = self.client.api_client.fetch_positions()
            positions = getattr(r, 'results', []) if hasattr(r, 'results') else (r.get("results", []) if isinstance(r, dict) else r)
            self._position_cache = positions
            self._position_cache_time = now
            return positions
        except:
            return []

    def get_position_size(self, market: str) -> Decimal:
        for p in self.get_positions():
            m = getattr(p, 'market', None) or (p.get('market') if isinstance(p, dict) else None)
            if m == market:
                sz = getattr(p, 'size', None) or (p.get('size') if isinstance(p, dict) else None)
                return abs(Decimal(str(sz)))
        return Decimal("0")

    @retry_on_error(max_retries=5, delay=2.0, backoff=1.5)
    def place_market_order(self, market: str, side: str, size: Decimal, reduce_only: bool = False) -> Optional[dict]:
        """執行市價單"""
        try:
            order = Order(
                market=market,
                order_type=OrderType.Market,
                order_side=OrderSide.Buy if side.upper() == "BUY" else OrderSide.Sell,
                size=size,
                client_id=f"{self.name}_{int(time.time()*1000)}",
                reduce_only=reduce_only,
            )
            r = self.client.api_client.submit_order(order=order)
            return {"id": getattr(r, 'id', None)} if r else {"ok": True}
        except Exception as e:
            print(f"[{self.name}] 市價單發送失敗: {e}")
            raise

    @retry_on_error(max_retries=3, delay=1.0)
    def cancel_all_orders(self, market: str = None) -> bool:
        """撤銷所有訂單"""
        params = {"market": market} if market else {}
        self.client.api_client.cancel_all_orders(params=params)
        return True