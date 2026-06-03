"""
远程调用模块
支持 HTTP REST 和 gRPC 协议
"""

import functools
import logging
import asyncio
from typing import Any, Callable, Optional

from pancake import oven

logger = logging.getLogger(__name__)


class HttpRemote:
    """HTTP REST 远程调用"""

    def __init__(self, base_url: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self._session

    async def call(self, endpoint: str, method: str = "POST",
                   data: dict = None, headers: dict = None) -> Any:
        """
        发起 HTTP 调用

        Args:
            endpoint: API 端点
            method: HTTP 方法
            data: 请求数据
            headers: 请求头

        Returns:
            响应数据
        """
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with session.request(method, url, json=data, headers=headers) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {text}")
                return await resp.json()
        except Exception as e:
            logger.error(f"HTTP 调用失败: {url} - {e}")
            raise

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


class GrpcRemote:
    """gRPC 远程调用"""

    def __init__(self, target: str = None):
        from pancake import settings
        self.target = target or settings.get("grpc.url")
        self._channel = None
        self._stubs = {}

    async def _get_channel(self):
        if self._channel is None:
            import grpc
            self._channel = grpc.aio.insecure_channel(self.target)
        return self._channel

    async def call(self, service: str, method: str, request: dict = None) -> Any:
        """
        发起 gRPC 调用

        Args:
            service: 服务名称
            method: 方法名称
            request: 请求数据

        Returns:
            响应数据
        """
        channel = await self._get_channel()

        try:
            # 动态调用 gRPC 方法
            stub = channel.unary_unary(
                f"/{service}/{method}",
                request_serializer=lambda x: str(x).encode(),
                response_deserializer=lambda x: x.decode()
            )
            response = await stub(request or {})
            return response
        except Exception as e:
            logger.error(f"gRPC 调用失败: {service}/{method} - {e}")
            raise

    async def close(self):
        if self._channel:
            await self._channel.close()
            self._channel = None


class RemoteProxy:
    """远程代理 - 统一远程调用接口"""

    def __init__(self):
        self._http_clients: dict[str, HttpRemote] = {}
        self._grpc_clients: dict[str, GrpcRemote] = {}

    def get_http(self, base_url: str, **kwargs) -> HttpRemote:
        """获取 HTTP 客户端"""
        if base_url not in self._http_clients:
            self._http_clients[base_url] = HttpRemote(base_url, **kwargs)
        return self._http_clients[base_url]

    def get_grpc(self, target: str, **kwargs) -> GrpcRemote:
        """获取 gRPC 客户端"""
        if target not in self._grpc_clients:
            self._grpc_clients[target] = GrpcRemote(target, **kwargs)
        return self._grpc_clients[target]

    async def close_all(self):
        """关闭所有连接"""
        for client in self._http_clients.values():
            await client.close()
        for client in self._grpc_clients.values():
            await client.close()
        self._http_clients.clear()
        self._grpc_clients.clear()


# 全局代理
proxy = RemoteProxy()


def remote_node(name: str = None, protocol: str = "http",
                url: str = None, service: str = None,
                endpoint: str = None, timeout: int = 30):
    """
    远程节点装饰器

    Args:
        name: 节点名称
        protocol: 协议 (http/grpc)
        url: HTTP 服务地址
        service: gRPC 服务名称
        endpoint: API 端点
        timeout: 超时时间
    """
    def decorator(func):
        nonlocal name
        if name is None:
            name = func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取函数参数
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            params = dict(bound.arguments)

            try:
                if protocol == "http":
                    if not url:
                        raise ValueError("HTTP 协议需要指定 url")
                    client = proxy.get_http(url, timeout=timeout)
                    result = await client.call(endpoint or name, data=params)
                elif protocol == "grpc":
                    if not service:
                        raise ValueError("gRPC 协议需要指定 service")
                    from pancake import settings
                    client = proxy.get_grpc(url or settings.get("grpc.url"))
                    result = await client.call(service, endpoint or name, params)
                else:
                    raise ValueError(f"不支持的协议: {protocol}")

                # 存储结果到共享 map
                oven.pancake_other.setdefault("langgraph_map", {})[name] = result
                return result

            except Exception as e:
                logger.error(f"远程节点 {name} 调用失败: {e}")
                raise

        # 标记为远程节点
        wrapper._remote = True
        wrapper._protocol = protocol
        wrapper._url = url
        wrapper._service = service

        # 注册到 langgraph 节点
        oven.pancake_dough.setdefault("langgraph_node", {})[name] = wrapper

        return wrapper
    return decorator
