"""Dough 系统测试"""

import pytest
from pancake.dough import Scope, DoughMeta
from pancake.registry import get_class, clear_registry


class TestScope:

    def test_scope_values(self):
        assert Scope.SINGLETON.value == "singleton"
        assert Scope.PROTOTYPE.value == "prototype"
        assert Scope.LAZY.value == "lazy"

    def test_scope_enum_members(self):
        assert len(Scope) == 3
        assert "SINGLETON" in [s.name for s in Scope]


class TestDoughMeta:

    def setup_method(self):
        clear_registry()

    def test_metaclass_registers_class(self):
        class MyClass(metaclass=DoughMeta):
            pass
        assert get_class("MyClass") is MyClass

    def test_metaclass_skips_dough_base(self):
        """名为 Dough 的类不自动注册"""
        class Dough(metaclass=DoughMeta):
            pass
        assert get_class("Dough") is None

    def test_metaclass_registers_subclass(self):
        class Base(metaclass=DoughMeta):
            pass
        class Child(Base):
            pass
        assert get_class("Child") is Child


class TestDough:

    def setup_method(self):
        clear_registry()

    def test_dough_is_abc(self):
        from pancake.dough import Dough
        from abc import ABC
        assert issubclass(Dough, ABC)

    def test_dough_uses_dough_meta(self):
        from pancake.dough import Dough
        assert type(Dough) is DoughMeta

    def test_dough_default_scope(self):
        from pancake.dough import Dough
        assert Dough._scope == Scope.SINGLETON

    def test_dough_default_lazy(self):
        from pancake.dough import Dough
        assert Dough._lazy is False

    def test_dough_lifecycle_methods_exist(self):
        from pancake.dough import Dough
        assert hasattr(Dough, "on_init")
        assert hasattr(Dough, "on_start")
        assert hasattr(Dough, "on_stop")
        assert hasattr(Dough, "on_destroy")

    @pytest.mark.asyncio
    async def test_dough_lifecycle_methods_are_noop(self):
        """默认生命周期方法是空操作"""
        from pancake.dough import Dough
        class MyBean(Dough):
            def __init__(self):
                pass
        bean = MyBean()
        # 不应抛出异常
        await bean.on_init()
        await bean.on_start()
        await bean.on_stop()
        await bean.on_destroy()

    def test_dough_subclass_auto_registered(self):
        from pancake.dough import Dough
        class MyBean(Dough):
            def __init__(self):
                pass
        assert get_class("MyBean") is MyBean

    def test_dough_not_abstract_on_init(self):
        """__init__ 不是抽象方法，子类可以不实现"""
        from pancake.dough import Dough
        class MyBean(Dough):
            pass
        # 不应抛出 TypeError
        bean = MyBean()
        assert bean is not None
