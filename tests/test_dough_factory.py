"""DoughFactory 测试"""

import pytest
from pancake.dough import Dough, Scope
from pancake.factory.dough_factory import DoughFactory


class MyBean(Dough):
    def __init__(self):
        self.value = 42


class TestDoughFactory:

    def setup_method(self):
        DoughFactory._factories.clear()

    def test_get_default_factory(self):
        factory = DoughFactory.get()
        assert factory.name == "default"

    def test_get_named_factory(self):
        factory = DoughFactory.get("test")
        assert factory.name == "test"

    def test_get_same_factory(self):
        f1 = DoughFactory.get("test")
        f2 = DoughFactory.get("test")
        assert f1 is f2

    def test_register_class(self):
        factory = DoughFactory.get()
        factory.register(MyBean)
        assert "MyBean" in factory._classes

    @pytest.mark.asyncio
    async def test_create_all_singleton(self):
        factory = DoughFactory.get()
        MyBean._scope = Scope.SINGLETON
        factory.register(MyBean)
        await factory.async_create_all()
        bean = factory.resolve("MyBean")
        assert isinstance(bean, MyBean)
        assert bean.value == 42

    @pytest.mark.asyncio
    async def test_resolve_singleton_returns_same(self):
        factory = DoughFactory.get()
        MyBean._scope = Scope.SINGLETON
        factory.register(MyBean)
        await factory.async_create_all()
        b1 = factory.resolve("MyBean")
        b2 = factory.resolve("MyBean")
        assert b1 is b2

    @pytest.mark.asyncio
    async def test_resolve_prototype_returns_new(self):
        factory = DoughFactory.get()
        MyBean._scope = Scope.PROTOTYPE
        factory.register(MyBean)
        await factory.async_create_all()
        b1 = factory.resolve("MyBean")
        b2 = factory.resolve("MyBean")
        assert b1 is not b2
        assert b1.value == b2.value == 42

    @pytest.mark.asyncio
    async def test_resolve_lazy_creates_on_first_access(self):
        factory = DoughFactory.get()
        MyBean._scope = Scope.LAZY
        factory.register(MyBean)
        await factory.async_create_all()
        assert "MyBean" not in factory._instances
        bean = factory.resolve("MyBean")
        assert isinstance(bean, MyBean)
        assert "MyBean" in factory._instances

    def test_resolve_unregistered_raises(self):
        factory = DoughFactory.get()
        with pytest.raises(ValueError, match="未注册"):
            factory.resolve("NonExistent")

    def test_register_instance(self):
        factory = DoughFactory.get()
        instance = MyBean()
        factory.register_instance("custom", instance)
        assert factory.resolve("custom") is instance

    @pytest.mark.asyncio
    async def test_lifecycle_on_init_called(self):
        class InitBean(Dough):
            def __init__(self):
                self.initialized = False
            async def on_init(self):
                self.initialized = True

        factory = DoughFactory.get()
        factory.register(InitBean)
        await factory.async_create_all()
        bean = factory.resolve("InitBean")
        assert bean.initialized is True

    @pytest.mark.asyncio
    async def test_lifecycle_startup_called(self):
        class StartBean(Dough):
            def __init__(self):
                self.started = False
            async def on_start(self):
                self.started = True

        factory = DoughFactory.get()
        factory.register(StartBean)
        await factory.async_create_all()
        await factory.async_startup_all()
        bean = factory.resolve("StartBean")
        assert bean.started is True

    @pytest.mark.asyncio
    async def test_shutdown_calls_on_stop_and_on_destroy(self):
        class StopBean(Dough):
            def __init__(self):
                self.stopped = False
                self.destroyed = False
            async def on_stop(self):
                self.stopped = True
            async def on_destroy(self):
                self.destroyed = True

        factory = DoughFactory.get()
        factory.register(StopBean)
        await factory.async_create_all()
        bean = factory.resolve("StopBean")
        await factory.async_shutdown_all()
        assert bean.stopped is True
        assert bean.destroyed is True

    def test_multiple_factories_independent(self):
        f1 = DoughFactory.get("f1")
        f2 = DoughFactory.get("f2")
        f1.register(MyBean)
        assert "MyBean" not in f2._classes

    @pytest.mark.asyncio
    async def test_sync_lifecycle_still_works(self):
        """同步生命周期方法仍然可以通过 async_create_all 调用"""
        class SyncBean(Dough):
            def __init__(self):
                self.done = False
            def on_init(self):
                self.done = True

        factory = DoughFactory.get()
        factory.register(SyncBean)
        await factory.async_create_all()
        bean = factory.resolve("SyncBean")
        assert bean.done is True


class TestDependencyResolution:

    def setup_method(self):
        DoughFactory._factories.clear()

    @pytest.mark.asyncio
    async def test_depends_on_creates_in_order(self):
        from pancake.decorators import DependsOn

        class DatabaseService(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                self.connected = True

        @DependsOn("DatabaseService")
        class UserService(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                self.db_ready = False
            async def on_init(self):
                db = DoughFactory.get().resolve("DatabaseService")
                self.db_ready = db.connected

        factory = DoughFactory.get()
        factory.register(DatabaseService)
        factory.register(UserService)
        await factory.async_create_all()

        user_svc = factory.resolve("UserService")
        assert user_svc.db_ready is True

    @pytest.mark.asyncio
    async def test_circular_dependency_raises(self):
        from pancake.decorators import DependsOn

        @DependsOn("ServiceB")
        class ServiceA(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                pass

        @DependsOn("ServiceA")
        class ServiceB(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                pass

        factory = DoughFactory.get()
        factory.register(ServiceA)
        factory.register(ServiceB)

        with pytest.raises(ValueError, match="循环依赖"):
            await factory.async_create_all()

    @pytest.mark.asyncio
    async def test_import_registers_classes(self):
        from pancake.decorators import Import

        class ExternalService(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                self.value = 99

        @Import(ExternalService)
        class AppConfig(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                pass

        factory = DoughFactory.get()
        factory.register(AppConfig)
        await factory.async_create_all()

        ext = factory.resolve("ExternalService")
        assert ext.value == 99

    @pytest.mark.asyncio
    async def test_chained_dependencies(self):
        from pancake.decorators import DependsOn

        creation_order = []

        class ServiceC(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                creation_order.append("ServiceC")

        @DependsOn("ServiceC")
        class ServiceB(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                creation_order.append("ServiceB")

        @DependsOn("ServiceB")
        class ServiceA(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                creation_order.append("ServiceA")

        factory = DoughFactory.get()
        factory.register(ServiceA)
        factory.register(ServiceB)
        factory.register(ServiceC)
        await factory.async_create_all()

        assert creation_order == ["ServiceC", "ServiceB", "ServiceA"]

    @pytest.mark.asyncio
    async def test_no_dependencies_still_works(self):
        class SimpleBean(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                self.ok = True

        factory = DoughFactory.get()
        factory.register(SimpleBean)
        await factory.async_create_all()
        assert factory.resolve("SimpleBean").ok is True

    @pytest.mark.asyncio
    async def test_depends_on_unknown_bean_ignored(self):
        from pancake.decorators import DependsOn

        @DependsOn("NonExistentBean")
        class MyBean(Dough):
            _scope = Scope.SINGLETON
            def __init__(self):
                self.created = True

        factory = DoughFactory.get()
        factory.register(MyBean)
        await factory.async_create_all()
        assert factory.resolve("MyBean").created is True
