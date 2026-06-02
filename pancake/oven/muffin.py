"""
Muffin 注册表
管理框架自带的装饰器、类、方法
"""


class MuffinRegistry:
    """
    Muffin 注册表 — 封装框架插件状态

    属性:
        flour: 装饰器 {"Mapper": ..., "get_controller": ...}
        water: 类 {"IoCContainer": ..., "Lifecycle": ...}
        egg:   方法/构建器 {"Builder": {}, "LoopMethod": {}}
        sugar: 其他 {"container": ...}
    """

    def __init__(self):
        self.flour: dict = {}
        self.water: dict = {}
        self.egg: dict = {}
        self.sugar: dict = {}

    def reset(self):
        """重置所有状态（用于测试）"""
        for d in (self.flour, self.water, self.egg, self.sugar):
            d.clear()


# 向后兼容的模块级默认实例
_registry = MuffinRegistry()

muffin_flour = _registry.flour
muffin_water = _registry.water
muffin_egg = _registry.egg
muffin_suger = _registry.sugar   # 保留旧拼写兼容
muffin_sugar = _registry.sugar   # 正确拼写


def create_registry() -> MuffinRegistry:
    """创建新的独立注册表（用于测试）"""
    return MuffinRegistry()
