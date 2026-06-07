"""基类测试"""

import pytest
from pancake.dough import Dough
from pancake.base.configuration import Configuration
from pancake.base.function import Function
from pancake.base.service import Service
from pancake.base.struct import Struct
from pancake.factory.dough_factory import DoughFactory


class TestConfiguration:

    def setup_method(self):
        DoughFactory._factories.clear()

    def test_configuration_is_dough(self):
        assert issubclass(Configuration, Dough)

    @pytest.mark.asyncio
    async def test_configuration_auto_registers_maker_methods(self):
        class AppConfig(Configuration):
            def __init__(self):
                pass
            def my_bean(self):
                return {"key": "value"}

        factory = DoughFactory.get()
        factory.register(AppConfig)
        await factory.async_create_all()
        assert factory.resolve("my_bean") == {"key": "value"}

    @pytest.mark.asyncio
    async def test_configuration_skips_private_methods(self):
        class AppConfig(Configuration):
            def __init__(self):
                pass
            def _private(self):
                return {"private": True}

        factory = DoughFactory.get()
        factory.register(AppConfig)
        await factory.async_create_all()
        with pytest.raises(ValueError):
            factory.resolve("_private")

    @pytest.mark.asyncio
    async def test_configuration_skips_no_maker(self):
        from pancake.decorators import noMaker
        class AppConfig(Configuration):
            def __init__(self):
                pass
            @noMaker
            def helper(self):
                return {"helper": True}

        factory = DoughFactory.get()
        factory.register(AppConfig)
        await factory.async_create_all()
        with pytest.raises(ValueError):
            factory.resolve("helper")

    @pytest.mark.asyncio
    async def test_configuration_skips_primitive_returns(self):
        class AppConfig(Configuration):
            def __init__(self):
                pass
            def get_name(self):
                return "test"
            def get_count(self):
                return 42

        factory = DoughFactory.get()
        factory.register(AppConfig)
        await factory.async_create_all()
        with pytest.raises(ValueError):
            factory.resolve("get_name")


class TestFunction:

    def test_function_is_dough(self):
        assert issubclass(Function, Dough)

    def test_function_is_callable(self):
        class MyFunc(Function):
            def call(self, x, y):
                return x + y

        f = MyFunc()
        assert f(1, 2) == 3

    def test_function_call_raises_not_implemented(self):
        f = Function()
        with pytest.raises(NotImplementedError):
            f.call()


class TestService:

    def test_service_is_dough(self):
        assert issubclass(Service, Dough)


class TestStruct:

    def test_struct_is_dough(self):
        assert issubclass(Struct, Dough)

    def test_struct_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(Struct)
