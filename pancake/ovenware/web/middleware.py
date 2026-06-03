"""
中间件模块
提供事务装饰器和限流装饰器
"""

import functools
import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def transaction(func: Callable) -> Callable:
    """事务装饰器 — 在数据库事务中执行路由

    装饰的路由函数会自动在事务内执行，异常时自动回滚。
    需要 mybatis 连接模块已初始化。
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from pancake.ovenware.mybatis.connection import get_database
        db = get_database()
        async with db.transaction():
            return await func(*args, **kwargs)
    return wrapper


# ============================================================
#  限流
# ============================================================

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_rate_limit_cleanup_counter: int = 0
_RATE_LIMIT_CLEANUP_INTERVAL: int = 1000  # 每 1000 次请求全量清理一次


def _rate_limit_cleanup():
    """清理所有过期的限流记录"""
    global _rate_limit_cleanup_counter
    _rate_limit_cleanup_counter += 1
    if _rate_limit_cleanup_counter < _RATE_LIMIT_CLEANUP_INTERVAL:
        return
    _rate_limit_cleanup_counter = 0
    now = time.time()
    expired_keys = [k for k, v in _rate_limit_store.items() if not v or now - v[-1] > 300]
    for k in expired_keys:
        del _rate_limit_store[k]


def rate_limit(times: int, seconds: int = 60):
    """限流装饰器 — 限制指定时间窗口内的请求次数

    基于客户端 IP 的滑动窗口限流，内存实现。

    用法:
        @get_controller("/api/data")
        @rate_limit(times=100, seconds=60)
        async def get_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{func.__name__}:{client_ip}"
            now = time.time()

            # 定期清理全局过期记录
            _rate_limit_cleanup()

            # 清理当前 key 的过期记录
            _rate_limit_store[key] = [
                t for t in _rate_limit_store[key] if now - t < seconds
            ]

            if len(_rate_limit_store[key]) >= times:
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请 {seconds} 秒后重试"
                )

            _rate_limit_store[key].append(now)
            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator
