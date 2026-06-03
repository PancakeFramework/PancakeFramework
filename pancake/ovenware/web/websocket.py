"""
WebSocket 控制器模块
"""

import logging
from typing import Callable

from fastapi import WebSocket

from pancake import oven

logger = logging.getLogger(__name__)

_websocket_registry: dict[str, Callable] = {}
_websocket_paths: dict[str, str] = {}


def websocket_controller(path: str, name: str = None):
    """WebSocket 控制器装饰器

    装饰的函数签名为 async def handler(websocket: WebSocket)

    用法:
        @websocket_controller("/ws/chat")
        async def chat(websocket: WebSocket):
            await websocket.accept()
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"Echo: {data}")
    """
    def decorator(func: Callable) -> Callable:
        nonlocal name
        if name is None:
            name = func.__name__
        _websocket_registry[name] = func
        _websocket_paths[name] = path
        logger.info(f"WebSocket {name} 已注册: {path}")
        return func
    return decorator
