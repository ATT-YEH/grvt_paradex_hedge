"""
统一时间工具模块
所有时间判断和显示都使用 UTC+8（北京时间）
"""
from datetime import datetime, timezone, timedelta
import time as _time

# UTC+8 时区
UTC8 = timezone(timedelta(hours=8))


def now_timestamp() -> float:
    """
    获取当前时间戳（秒）
    注意：时间戳本身是 UTC 标准，与时区无关
    """
    return _time.time()


def now_utc8() -> datetime:
    """
    获取当前 UTC+8 时间的 datetime 对象
    """
    return datetime.now(UTC8)


def strftime(fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化当前 UTC+8 时间为字符串

    Args:
        fmt: 时间格式，默认 '%Y-%m-%d %H:%M:%S'

    Returns:
        格式化后的时间字符串
    """
    return now_utc8().strftime(fmt)


def timestamp_to_utc8(timestamp: float, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    将时间戳转换为 UTC+8 时间字符串

    Args:
        timestamp: Unix 时间戳（秒）
        fmt: 时间格式

    Returns:
        格式化后的 UTC+8 时间字符串
    """
    dt = datetime.fromtimestamp(timestamp, UTC8)
    return dt.strftime(fmt)


def localtime(timestamp: float):
    """
    将时间戳转换为 UTC+8 的 time.struct_time
    兼容 time.localtime() 的用法

    Args:
        timestamp: Unix 时间戳（秒）

    Returns:
        time.struct_time 对象
    """
    dt = datetime.fromtimestamp(timestamp, UTC8)
    return dt.timetuple()


# 兼容性别名
time = now_timestamp
