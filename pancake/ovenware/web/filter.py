"""
Filter Chain 模块
类似 Spring Security 的过滤器链机制

支持两种写法：
  函数式: @filter(order=10) 装饰 async def handler(request, call_next)
  类继承: class MyFilter(Filter): order = 10; async def do_filter(self, request, call_next)
"""

import logging
import time
from typing import Callable

from fastapi import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_filter_registry: list[dict] = []


class Filter:
    """Filter 基类 — 继承并实现 do_filter 方法

    子类定义时自动注册到 filter chain。

    用法:
        class AuthFilter(Filter):
            order = 10

            async def do_filter(self, request, call_next):
                if not request.headers.get("Authorization"):
                    return JSONResponse(status_code=401, content={"detail": "未认证"})
                return await call_next(request)
    """
    order: int = 0
    name: str = ""

    async def do_filter(self, request: Request, call_next) -> Response:
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 跳过未实现 do_filter 的中间抽象类
        if cls.do_filter is Filter.do_filter:
            return
        instance = cls()
        filter_name = instance.name or cls.__name__
        _filter_registry.append({
            "func": instance.do_filter,
            "order": instance.order,
            "name": filter_name,
        })
        _filter_registry.sort(key=lambda x: x["order"])
        logger.info(f"Filter {filter_name} 已注册 (order={instance.order})")


def filter(order: int = 0, name: str = None):
    """Filter 装饰器 — 注册请求过滤器（函数式）

    签名: async def handler(request: Request, call_next) -> Response
    - call_next(request): 继续执行下一个 filter
    - 直接 return Response: 中断链路，返回响应

    用法:
        @filter(order=10)
        async def auth_filter(request: Request, call_next):
            if not request.headers.get("Authorization"):
                return JSONResponse(status_code=401, content={"detail": "未认证"})
            return await call_next(request)
    """
    def decorator(func: Callable) -> Callable:
        filter_name = name or func.__name__
        _filter_registry.append({"func": func, "order": order, "name": filter_name})
        _filter_registry.sort(key=lambda x: x["order"])
        logger.info(f"Filter {filter_name} 已注册 (order={order})")
        return func
    return decorator


# 向后兼容：旧 middleware 装饰器等价于 filter
def middleware(order: int = 0):
    """中间件装饰器（向后兼容，等价于 @filter）"""
    return filter(order=order)


class MetricsFilter(Filter):
    """内置指标收集 Filter"""
    order = 900
    name = "metrics"

    async def do_filter(self, request: Request, call_next) -> Response:
        from .metrics import _record_metric
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        _record_metric(request.url.path, request.method, response.status_code, duration)
        return response
