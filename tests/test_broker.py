"""消息队列测试"""

import pytest
import asyncio
from pancake.ovenware.broker import (
    SimpleBroker, MessageBroker, BrokerManager,
    create_manager, get_broker, set_broker,
)


class TestSimpleBroker:

    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        broker = SimpleBroker()
        received = []

        async def handler(msg):
            received.append(msg)

        await broker.subscribe("test_topic", handler)
        await broker.publish("test_topic", {"data": "hello"})

        assert len(received) == 1
        assert received[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        broker = SimpleBroker()
        results_a = []
        results_b = []

        await broker.subscribe("t", lambda m: results_a.append(m))
        await broker.subscribe("t", lambda m: results_b.append(m))
        await broker.publish("t", {"x": 1})

        assert len(results_a) == 1
        assert len(results_b) == 1

    @pytest.mark.asyncio
    async def test_no_subscribers(self):
        broker = SimpleBroker()
        # 不应报错
        await broker.publish("no_topic", {"x": 1})

    @pytest.mark.asyncio
    async def test_handler_exception_logged(self):
        broker = SimpleBroker()
        success = []

        async def bad_handler(msg):
            raise RuntimeError("boom")

        async def good_handler(msg):
            success.append(msg)

        await broker.subscribe("t", bad_handler)
        await broker.subscribe("t", good_handler)
        await broker.publish("t", {"x": 1})

        # good_handler 仍然被调用
        assert len(success) == 1

    @pytest.mark.asyncio
    async def test_close(self):
        broker = SimpleBroker()
        await broker.subscribe("t", lambda m: None)
        await broker.close()
        assert broker._handlers == {}


class TestBrokerManager:

    def test_get_creates_default(self):
        manager = BrokerManager()
        broker = manager.get()
        assert isinstance(broker, SimpleBroker)

    def test_get_returns_same_instance(self):
        manager = BrokerManager()
        b1 = manager.get()
        b2 = manager.get()
        assert b1 is b2

    def test_set_custom_broker(self):
        manager = BrokerManager()
        custom = SimpleBroker()
        manager.set(custom)
        assert manager.get() is custom

    def test_reset(self):
        manager = BrokerManager()
        manager.get()
        manager.reset()
        # get after reset creates new instance
        b = manager.get()
        assert isinstance(b, SimpleBroker)

    def test_create_manager_factory(self):
        m1 = create_manager()
        m2 = create_manager()
        assert m1 is not m2

    def test_backward_compat_functions(self):
        """模块级函数仍然可用"""
        assert callable(get_broker)
        assert callable(set_broker)
