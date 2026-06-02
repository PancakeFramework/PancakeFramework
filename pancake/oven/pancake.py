"""
Pancake 注册表
管理框架全局状态：配置、注册的类、实例化的对象、运行时数据
"""


class PancakeRegistry:
    """
    Pancake 注册表 — 封装框架全局状态

    属性:
        json:  JSON 配置
        yaml:  YAML 配置（扁平化 key）
        xml:   XML 配置（插件参数 + 全局配置）
        dough: 注册的类 {"Service": {}, "Mapper": {}}
        pie:   实例化的对象 {"Service": {}, "Method": {}, "Mapper": {}}
        other: 运行时数据 {"path": {}, "System": {}}
    """

    def __init__(self):
        self.json: dict = {}
        self.yaml: dict = {}
        self.xml: dict = {}
        self.dough: dict = {}
        self.pie: dict = {}
        self.other: dict = {}

    def reset(self):
        """重置所有状态（用于测试）"""
        for d in (self.json, self.yaml, self.xml, self.dough, self.pie, self.other):
            d.clear()


# 向后兼容的模块级默认实例
_registry = PancakeRegistry()

pancake_json = _registry.json
pancake_yaml = _registry.yaml
pancake_xml = _registry.xml
pancake_dough = _registry.dough
pancake_pie = _registry.pie
pancake_other = _registry.other


def create_registry() -> PancakeRegistry:
    """创建新的独立注册表（用于测试）"""
    return PancakeRegistry()
