"""Decorators 测试"""

import pytest
from pancake.dough import Dough, Scope
from pancake.decorators import (
    DependsOn, Import, DoughDecorator, Singleton, Prototype, Lazy,
    Maker, noMaker, inject, Config,
)


class TestDependsOn:

    def test_depends_on_sets_attribute(self):
        @DependsOn("ServiceA", "ServiceB")
        class MyService(Dough):
            def __init__(self):
                pass

        assert MyService._depends_on == ["ServiceA", "ServiceB"]

    def test_depends_on_empty(self):
        @DependsOn()
        class EmptyDeps(Dough):
            def __init__(self):
                pass

        assert EmptyDeps._depends_on == []

    def test_depends_on_preserves_class(self):
        """装饰器不改变类本身"""
        @DependsOn("X")
        class Original(Dough):
            def __init__(self):
                self.marker = 123

        assert Original().marker == 123
        assert Original.__name__ == "Original"


class TestImport:

    def test_import_sets_attribute(self):
        class External(Dough):
            def __init__(self):
                pass

        @Import(External)
        class Config(Dough):
            def __init__(self):
                pass

        assert Config._imports == [External]

    def test_import_multiple_classes(self):
        class A(Dough):
            def __init__(self):
                pass

        class B(Dough):
            def __init__(self):
                pass

        @Import(A, B)
        class Config(Dough):
            def __init__(self):
                pass

        assert Config._imports == [A, B]

    def test_import_preserves_class(self):
        """装饰器不改变类本身"""
        class External(Dough):
            def __init__(self):
                pass

        @Import(External)
        class Config(Dough):
            def __init__(self):
                self.val = 42

        assert Config().val == 42
        assert Config.__name__ == "Config"


class TestClassDecorators:

    def test_dough_decorator_sets_scope(self):
        @DoughDecorator
        class MyBean(Dough):
            def __init__(self):
                pass
        assert MyBean._scope == Scope.SINGLETON

    def test_singleton_decorator(self):
        @Singleton
        class MyBean(Dough):
            def __init__(self):
                pass
        assert MyBean._scope == Scope.SINGLETON

    def test_prototype_decorator(self):
        @Prototype
        class MyBean(Dough):
            def __init__(self):
                pass
        assert MyBean._scope == Scope.PROTOTYPE

    def test_lazy_decorator(self):
        @Lazy
        class MyBean(Dough):
            def __init__(self):
                pass
        assert MyBean._lazy is True
        assert MyBean._scope == Scope.LAZY

    def test_decorator_composition(self):
        @Prototype
        @DoughDecorator
        class MyBean(Dough):
            def __init__(self):
                pass
        assert MyBean._scope == Scope.PROTOTYPE


class TestMakerDecorator:

    def test_maker_marks_method(self):
        class MyConfig(Dough):
            def __init__(self):
                pass
            @Maker
            def my_bean(self):
                return "bean"
        assert hasattr(MyConfig.my_bean, "_is_maker")
        assert MyConfig.my_bean._is_maker is True


class TestNoMakerDecorator:

    def test_no_maker_marks_method(self):
        class MyConfig(Dough):
            def __init__(self):
                pass
            @noMaker
            def helper(self):
                return "helper"
        assert hasattr(MyConfig.helper, "_no_maker")
        assert MyConfig.helper._no_maker is True


class TestInjectDecorator:

    def test_inject_sync_function(self):
        """@inject 正确包装同步函数"""
        @inject
        def hello(name: str = "world"):
            return f"hello {name}"
        result = hello()
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_inject_async_function(self):
        """@inject 正确包装异步函数"""
        @inject
        async def hello(name: str = "world"):
            return f"hello {name}"
        result = await hello()
        assert result == "hello world"

    def test_inject_preserves_async_flag(self):
        """@inject 保留 async 特性"""
        import inspect
        @inject
        async def async_func():
            pass
        assert inspect.iscoroutinefunction(async_func)

    def test_inject_preserves_sync_flag(self):
        """@inject 保留 sync 特性"""
        import inspect
        @inject
        def sync_func():
            pass
        assert not inspect.iscoroutinefunction(sync_func)
