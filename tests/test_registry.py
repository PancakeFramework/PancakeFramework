"""注册表测试"""

from pancake.oven.pancake import PancakeRegistry, create_registry
from pancake.oven.muffin import MuffinRegistry, create_registry as create_muffin


class TestPancakeRegistry:

    def test_create_empty(self, pancake_registry):
        assert pancake_registry.json == {}
        assert pancake_registry.yaml == {}
        assert pancake_registry.xml == {}
        assert pancake_registry.dough == {}
        assert pancake_registry.pie == {}
        assert pancake_registry.other == {}

    def test_independent_instances(self):
        r1 = PancakeRegistry()
        r2 = PancakeRegistry()
        r1.yaml["key"] = "value"
        assert "key" not in r2.yaml

    def test_reset(self, pancake_registry):
        pancake_registry.yaml["a"] = 1
        pancake_registry.dough["Service"] = {}
        pancake_registry.reset()
        assert pancake_registry.yaml == {}
        assert pancake_registry.dough == {}

    def test_create_registry_factory(self):
        r = create_registry()
        assert isinstance(r, PancakeRegistry)
        r2 = create_registry()
        assert r is not r2


class TestMuffinRegistry:

    def test_create_empty(self, muffin_registry):
        assert muffin_registry.flour == {}
        assert muffin_registry.water == {}
        assert muffin_registry.egg == {}
        assert muffin_registry.sugar == {}

    def test_independent_instances(self):
        r1 = MuffinRegistry()
        r2 = MuffinRegistry()
        r1.flour["Mapper"] = lambda cls: cls
        assert "Mapper" not in r2.flour

    def test_reset(self, muffin_registry):
        muffin_registry.flour["x"] = 1
        muffin_registry.egg["y"] = 2
        muffin_registry.reset()
        assert muffin_registry.flour == {}
        assert muffin_registry.egg == {}

    def test_create_registry_factory(self):
        r = create_muffin()
        assert isinstance(r, MuffinRegistry)

    def test_backward_compat_sugar_alias(self):
        """muffin_suger 和 muffin_sugar 指向同一个 dict"""
        from pancake.oven import muffin
        assert muffin.muffin_suger is muffin.muffin_sugar
