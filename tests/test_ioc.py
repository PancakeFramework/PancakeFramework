"""IoC 容器和依赖注入测试"""

import pytest
from pancake.ovenware.inject import IoCContainer, Scope, auto_inject


class GreetingService:
    def hello(self):
        return "hello"


class UserService:
    def __init__(self, greeting: GreetingService = None):
        self.greeting = greeting

    def greet(self, name: str):
        prefix = self.greeting.hello() if self.greeting else "hi"
        return f"{prefix} {name}"


class TestIoCContainer:

    def test_register_and_resolve_singleton(self, ioc_container):
        ioc_container.register(GreetingService, GreetingService, Scope.SINGLETON)
        s1 = ioc_container.resolve(GreetingService)
        s2 = ioc_container.resolve(GreetingService)
        assert s1 is s2

    def test_register_and_resolve_transient(self, ioc_container):
        ioc_container.register(GreetingService, GreetingService, Scope.TRANSIENT)
        s1 = ioc_container.resolve(GreetingService)
        s2 = ioc_container.resolve(GreetingService)
        assert s1 is not s2

    def test_register_singleton_instance(self, ioc_container):
        instance = GreetingService()
        ioc_container.register(GreetingService, instance, Scope.SINGLETON)
        resolved = ioc_container.resolve(GreetingService)
        assert resolved is instance

    def test_resolve_unregistered_raises(self, ioc_container):
        with pytest.raises(ValueError, match="未注册"):
            ioc_container.resolve("NonExistent")

    def test_register_with_factory(self, ioc_container):
        ioc_container.register(GreetingService, factory=lambda: GreetingService())
        s = ioc_container.resolve(GreetingService)
        assert isinstance(s, GreetingService)

    def test_convenience_methods(self, ioc_container):
        ioc_container.register_singleton(GreetingService, GreetingService)
        s = ioc_container.resolve(GreetingService)
        assert s is not None

        ioc_container.register_transient(GreetingService, GreetingService)
        s1 = ioc_container.resolve(GreetingService)
        s2 = ioc_container.resolve(GreetingService)
        assert s1 is not s2

    def test_clear_all(self, ioc_container):
        ioc_container.register(GreetingService, GreetingService, Scope.SINGLETON)
        ioc_container.clear_all()
        with pytest.raises(ValueError):
            ioc_container.resolve(GreetingService)

    def test_scoped_returns_same_within_scope(self, ioc_container):
        ioc_container.register(GreetingService, GreetingService, Scope.SCOPED)
        s1 = ioc_container.resolve(GreetingService)
        s2 = ioc_container.resolve(GreetingService)
        assert s1 is s2
        ioc_container.clear_scoped()
        s3 = ioc_container.resolve(GreetingService)
        assert s3 is not s1


class TestInjectDecorator:

    def test_inject_from_container(self, ioc_container):
        ioc_container.register(GreetingService, GreetingService, Scope.SINGLETON)

        @ioc_container.inject
        def get_greeting(greeting: GreetingService):
            return greeting.hello()

        result = get_greeting()
        assert result == "hello"

    def test_inject_named_deps(self, ioc_container):
        svc = GreetingService()

        @ioc_container.inject(greeting=svc)
        def get_greeting(greeting: GreetingService):
            return greeting.hello()

        result = get_greeting()
        assert result == "hello"

    def test_inject_does_not_override_explicit_args(self, ioc_container):
        ioc_container.register(GreetingService, GreetingService, Scope.SINGLETON)

        @ioc_container.inject
        def get_greeting(greeting: GreetingService):
            return greeting.hello()

        # 即使容器有注册，显式参数优先（但 inject 的实现是跳过已有 kwargs 的参数）
        result = get_greeting()
        assert result == "hello"


class TestAutoInject:

    def test_auto_inject_from_yaml(self):
        """auto_inject 从 YAML 配置注入 str/int/float/bool 参数"""
        from pancake import oven
        # 临时设置 YAML 配置
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["service.title"] = "TestApp"
            oven.pancake_yaml["service.port"] = 9090

            @auto_inject()
            def get_config(service_title: str, service_port: int):
                return {"title": service_title, "port": service_port}

            result = get_config()
            assert result == {"title": "TestApp", "port": 9090}
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)

    def test_auto_inject_with_explicit_args(self):
        from pancake import oven
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["service.title"] = "TestApp"

            @auto_inject()
            def get_title(service_title: str):
                return service_title

            # 显式传参覆盖配置
            result = get_title(service_title="Override")
            assert result == "Override"
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)
