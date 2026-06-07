"""
全局注册表
无依赖，解决循环导入问题
提供类注册表和装饰器注册表
"""

_class_registry: dict[str, type] = {}
_decorator_registry: dict[str, object] = {}


# ---- 类注册表 ----

def register_class(name: str, cls: type):
    """注册类到全局注册表"""
    _class_registry[name] = cls


def get_class(name: str) -> type | None:
    """从注册表获取类"""
    return _class_registry.get(name)


def get_all_classes() -> dict[str, type]:
    """获取所有注册的类（返回副本）"""
    return dict(_class_registry)


# ---- 装饰器注册表 ----

def register_decorator(name: str, decorator: object):
    """注册装饰器到全局注册表"""
    _decorator_registry[name] = decorator


def get_decorator(name: str) -> object | None:
    """从注册表获取装饰器"""
    return _decorator_registry.get(name)


def get_all_decorators() -> dict[str, object]:
    """获取所有注册的装饰器（返回副本）"""
    return dict(_decorator_registry)


def has_decorator(name: str) -> bool:
    """检查装饰器是否已注册"""
    return name in _decorator_registry


# ---- 清理 ----

def clear_registry():
    """清空所有注册表（用于测试）"""
    _class_registry.clear()
    _decorator_registry.clear()


# ---- 注册到 muffin_water，供 Dough.on_init 零 import 注入 ----

def _register_to_muffin():
    from pancake.oven.muffin import muffin_water
    muffin_water["register_class"] = register_class
    muffin_water["get_class"] = get_class
    muffin_water["get_all_classes"] = get_all_classes
    muffin_water["register_decorator"] = register_decorator
    muffin_water["get_decorator"] = get_decorator
    muffin_water["get_all_decorators"] = get_all_decorators

_register_to_muffin()
