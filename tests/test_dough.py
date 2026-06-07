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
