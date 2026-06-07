"""
消息队列模块
支持事件驱动和消息传递
"""

import asyncio
import functools
import logging
from typing import Any, Callable
from collections import defaultdict

from pancake.dough import Dough, Scope
from pancake.registry import register_decorator

logger = logging.getLogger(__name__)


class MessageBroker(Dough):
    """消息队列基类"""

    async def publish(self, topic: str, message: dict) -> None:
        """发布消息"""
        raise NotImplementedError

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """订阅主题"""
        raise NotImplementedError

    async def close(self) -> None:
        """关闭连接"""
        pass


# 延迟订阅队列：on_event 注册的 handler 在首次 publish 时自动订阅
_pending_subscriptions: dict[str, list[Callable]] = defaultdict(list)


class SimpleBroker(MessageBroker):
    """简单内存消息队列"""

    _scope = Scope.SINGLETON

    def __init__(self):
        super().__init__()
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._initialized = False

    def _setup_pending(self):
        """将 on_event 注册的延迟 handler 合并到 _handlers"""
        if not self._initialized:
            for topic, handlers in _pending_subscriptions.items():
                for h in handlers:
                    if h not in self._handlers[topic]:
                        self._handlers[topic].append(h)
            self._initialized = True

    async def publish(self, topic: str, message: dict) -> None:
        """发布消息并立即触发处理"""
        self._setup_pending()
        await self._process_message(topic, message)

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """订阅主题"""
        self._handlers[topic].append(handler)
        logger.info(f"订阅主题: {topic}")

    async def _process_message(self, topic: str, message: dict) -> None:
        """处理消息"""
        handlers = self._handlers.get(topic, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"处理消息失败 [{topic}]: {e}")

    async def close(self):
        """关闭并清理"""
        self._handlers.clear()

    async def on_destroy(self):
        """销毁时清理"""
        self._handlers.clear()


class RedisBroker(MessageBroker):
    """Redis 消息队列"""

    _scope = Scope.SINGLETON

    def __init__(self, url: str = None):
        super().__init__()
        from pancake import settings
        self.url = url or settings.get("redis.url")
        self._redis = None
        self._pubsub = None
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._listener_task = None
        self._initialized = False

    async def _setup_pending(self):
        """将 on_event 注册的延迟 handler 合并并订阅"""
        if not self._initialized:
            for topic, handlers in _pending_subscriptions.items():
                for h in handlers:
                    if h not in self._handlers[topic]:
                        self._handlers[topic].append(h)
                        redis = await self._get_redis()
                        if self._pubsub is None:
                            self._pubsub = redis.pubsub()
                        await self._pubsub.subscribe(topic)
            if self._listener_task is None and self._handlers:
                self._listener_task = asyncio.create_task(self._listen())
            self._initialized = True

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self.url)
        return self._redis

    async def publish(self, topic: str, message: dict) -> None:
        """发布消息到 Redis"""
        await self._setup_pending()
        redis = await self._get_redis()
        import json
        await redis.publish(topic, json.dumps(message))
        logger.debug(f"发布消息到 {topic}")

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """订阅 Redis 主题"""
        self._handlers[topic].append(handler)

        # 启动监听器
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._listen())

        redis = await self._get_redis()
        if self._pubsub is None:
            self._pubsub = redis.pubsub()

        await self._pubsub.subscribe(topic)
        logger.info(f"订阅 Redis 主题: {topic}")

    async def _listen(self) -> None:
        """监听 Redis 消息（指数退避重试）"""
        import json
        consecutive_failures = 0
        max_backoff = 30  # 最大退避时间（秒）
        max_failures = 10  # 连续失败超过此次数停止重试

        while True:
            try:
                if self._pubsub:
                    message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "message":
                        topic = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                        data = json.loads(message["data"])
                        await self._process_message(topic, data)
                    consecutive_failures = 0  # 成功接收，重置计数
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger.error(f"Redis 监听连续失败 {consecutive_failures} 次，停止重试: {e}")
                    break
                backoff = min(2 ** (consecutive_failures - 1), max_backoff)
                logger.warning(f"Redis 监听错误 (第 {consecutive_failures} 次，{backoff}s 后重试): {e}")
                await asyncio.sleep(backoff)

    async def _process_message(self, topic: str, message: dict) -> None:
        """处理消息"""
        handlers = self._handlers.get(topic, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"处理消息失败 [{topic}]: {e}")

    async def on_destroy(self):
        """销毁时清理连接"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        if self._redis:
            await self._redis.close()
            self._redis = None


class BrokerManager:
    """
    消息队列管理器 — 封装全局 broker 状态

    使用方法:
        manager = BrokerManager()
        broker = manager.get()       # 默认 SimpleBroker
        manager.set(RedisBroker())
        manager.reset()
    """

    def __init__(self):
        self._broker: MessageBroker | None = None

    def get(self) -> MessageBroker:
        """获取全局 broker（懒初始化为 SimpleBroker）"""
        if self._broker is None:
            self._broker = SimpleBroker()
        return self._broker

    def set(self, broker: MessageBroker) -> None:
        """设置全局 broker"""
        self._broker = broker

    def reset(self) -> None:
        """重置状态（用于测试）"""
        self._broker = None


# 向后兼容的模块级默认实例
_manager = BrokerManager()

get_broker = _manager.get
set_broker = _manager.set


def create_manager() -> BrokerManager:
    """创建新的独立管理器（用于测试）"""
    return BrokerManager()


def event_node(name: str = None, event: str = None):
    """
    事件节点装饰器

    Args:
        name: 节点名称
        event: 事件名称（用于消息队列）
    """
    def decorator(func):
        nonlocal name
        if name is None:
            name = func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            # 发布事件
            if event:
                broker = get_broker()
                await broker.publish(event, {
                    "source": name,
                    "result": result,
                    "data": kwargs,
                })

            # 存储结果到 registry
            from pancake.factory.dough_factory import DoughFactory
            factory = DoughFactory.get()
            factory.register_instance(f"langgraph_result_{name}", result)
            return result

        # 标记为事件节点
        wrapper._event = True
        wrapper._event_name = event

        return wrapper
    return decorator


def on_event(event: str):
    """
    事件监听装饰器

    Args:
        event: 事件名称
    """
    def decorator(func):
        _pending_subscriptions[event].append(func)
        func._event_name = event
        return func
    return decorator


# 注册装饰器到全局注册表
register_decorator("event_node", event_node)
register_decorator("on_event", on_event)
