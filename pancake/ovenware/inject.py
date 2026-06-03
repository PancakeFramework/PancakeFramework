"""
统一依赖注入模块
合并 IoC 容器和 auto_inject 配置注入

提供 3 种注入方式：
  @auto_inject()   — 从 YAML/JSON 配置自动填充函数参数
  IoCContainer     — 对象容器，管理单例/瞬态/作用域
  @inject          — 从 IoC 容器注入对象到函数参数
"""

import functools
import inspect
import logging
import threading
from enum import Enum
from typing import Any, Callable, Type, get_type_hints

from pancake import oven

logger = logging.getLogger(__name__)


# ============================================================
#  auto_inject — 从配置注入值
# ============================================================

def _get_param_types(func):
    """获取函数参数类型注解（跳过 *args、**kwargs 和无注解参数）"""
    sig = inspect.signature(func)
    param_types = {}
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        param_types[name] = param.annotation
    return param_types


def auto_inject(*same_name_args: list[str], **customize_args: dict[str, str]):
    """
    自动注入装饰器 — 从 YAML/JSON 配置填充参数

    参数类型决定数据来源：
      str/int/float/bool → pancake_yaml（配置值）
      dict/list          → pancake_json
      其他               → pancake_pie（实例）

    使用方法：
        @auto_inject()
        def get_config(service_title: str, service_port: int):
            return {"title": service_title, "port": service_port}

        # service_title 自动从 YAML 的 service.title 获取
        get_config()
    """
    def decorator(func):
        nonlocal same_name_args
        param_types = _get_param_types(func)

        first_param_is_self_cls = False
        param_names = list(param_types.keys())
        if param_names and param_names[0] in ('self', 'cls'):
            param_types.pop(param_names[0])
            first_param_is_self_cls = True

        # 检查参数数量是否正确
        len_param_types = len(param_types)
        len_args = len(same_name_args) + len(customize_args)
        if len_args == 0:
            same_name_args = list(param_types.keys())
        elif len_args != len_param_types:
            logger.error(f"调用函数 {func.__name__}, 参数数量错误, 应该是 {len_param_types}")
            raise ValueError(f"参数数量错误, 应该是 {len_param_types}")

        for param_item in customize_args.keys():
            if param_item not in param_types.keys():
                logger.error(f"调用函数 {func.__name__}, 参数 {param_item} 不存在")
                raise ValueError(f"参数 {param_item} 不存在")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if first_param_is_self_cls:
                cls_or_self = args[0]
                args = args[1:]
            args_len = len(args)
            kwargs_len = len(kwargs)

            if args_len + kwargs_len > len_param_types:
                logger.error(f"调用函数 {func.__name__}, 参数数量错误, 最多是 {len_param_types}")
                raise ValueError(f"参数数量错误, 最多是 {len_param_types}")

            # 检查参数类型
            for param_item_ in kwargs.keys():
                try:
                    if not isinstance(kwargs[param_item_], param_types[param_item_]) and kwargs[param_item_] is not None:
                        logger.error(f"调用函数 {func.__name__}, 参数 {param_item_} 类型错误, 应该是 {param_types[param_item_]}")
                        raise TypeError(f"参数 {param_item_} 类型错误, 应该是 {param_types[param_item_]}")
                except KeyError:
                    logger.error(f"调用函数 {func.__name__}, 参数 {param_item_} 不存在")
                    raise ValueError(f"参数 {param_item_} 不存在")
            for index, arg in enumerate(args):
                param_type = list(param_types.values())[index]
                if param_type == inspect.Parameter.empty:
                    continue
                if not isinstance(arg, param_type) and arg is not None:
                    logger.error(f"调用函数 {func.__name__}, 第 {index} 个参数 类型错误, 应该是 {param_type}")

            # 自动注入缺失参数
            inject_args = [x for x in list(param_types.keys())[args_len:] if x not in kwargs.keys()]
            for param_item_ in inject_args:
                if param_item_ not in same_name_args:
                    param_item_ = customize_args[param_item_]
                try:
                    match param_types[param_item_]:
                        case type() as t if t in (str, int, float, bool):
                            yaml_key = param_item_.replace("_", ".")
                            kwargs[param_item_] = oven.pancake_yaml[yaml_key]
                        case type() as t if t in (dict, list):
                            kwargs[param_item_] = oven.pancake_json[param_item_]
                        case _:
                            kwargs[param_item_] = oven.pancake_pie[param_item_]
                except KeyError:
                    try:
                        kwargs[param_item_] = oven.pancake_other[param_item_]
                    except KeyError:
                        logger.error(f"调用函数 {func.__name__}, 参数 {param_item_} 不存在")
                        raise ValueError(f"参数 {param_item_} 不存在")

            if first_param_is_self_cls:
                args = (cls_or_self,) + args
            return func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================
#  IoC 容器 — 对象依赖注入
# ============================================================

class Scope(Enum):
    """依赖作用域"""
    SINGLETON = "singleton"    # 单例 - 全局唯一
    TRANSIENT = "transient"    # 瞬态 - 每次创建新实例
    SCOPED = "scoped"          # 作用域 - 同一流程内单例


class IoCContainer:
    """IoC 容器 - 管理依赖注册和解析"""

    def __init__(self):
        self._registrations: dict[str, dict] = {}
        self._singletons: dict[str, Any] = {}
        self._scoped: dict[str, Any] = {}
        self._resolving: set[str] = set()  # 循环依赖检测
        self._lock = threading.Lock()  # 线程安全

    def register(self, interface: Type = None, implementation: Any = None,
                 scope: Scope = Scope.TRANSIENT, factory: Callable = None):
        """
        注册依赖

        Args:
            interface: 接口类型（或类名）
            implementation: 实现类或实例
            scope: 作用域
            factory: 工厂函数
        """
        key = interface.__name__ if interface else implementation.__name__
        self._registrations[key] = {
            "interface": interface,
            "implementation": implementation,
            "scope": scope,
            "factory": factory,
        }
        if scope == Scope.SINGLETON and implementation and not inspect.isclass(implementation):
            self._singletons[key] = implementation
        logger.info(f"IoC 注册: {key} ({scope.value})")

    def register_singleton(self, interface: Type, implementation: Any = None):
        self.register(interface, implementation, Scope.SINGLETON)

    def register_transient(self, interface: Type, implementation: Any = None):
        self.register(interface, implementation, Scope.TRANSIENT)

    def register_scoped(self, interface: Type, implementation: Any = None):
        self.register(interface, implementation, Scope.SCOPED)

    def resolve(self, interface: Type) -> Any:
        """
        解析依赖

        Args:
            interface: 接口类型

        Returns:
            解析后的实例
        """
        key = interface.__name__ if inspect.isclass(interface) else interface
        if key not in self._registrations:
            raise ValueError(f"未注册的依赖: {key}")

        reg = self._registrations[key]
        scope = reg["scope"]

        # 快速路径：已缓存的单例/作用域，无需加锁
        if scope == Scope.SINGLETON and key in self._singletons:
            return self._singletons[key]
        if scope == Scope.SCOPED and key in self._scoped:
            return self._scoped[key]

        # 加锁创建实例（double-checked locking）
        with self._lock:
            # 再次检查缓存
            if scope == Scope.SINGLETON and key in self._singletons:
                return self._singletons[key]
            if scope == Scope.SCOPED and key in self._scoped:
                return self._scoped[key]

            # 循环依赖检测
            if key in self._resolving:
                chain = " -> ".join(self._resolving) + f" -> {key}"
                raise ValueError(f"检测到循环依赖: {chain}")

            self._resolving.add(key)
            try:
                instance = self._create_instance(reg)
            finally:
                self._resolving.discard(key)

            if scope == Scope.SINGLETON:
                self._singletons[key] = instance
            elif scope == Scope.SCOPED:
                self._scoped[key] = instance

        return instance

    def _create_instance(self, reg: dict) -> Any:
        if reg["factory"]:
            return reg["factory"]()
        impl = reg["implementation"]
        if not inspect.isclass(impl):
            return impl
        sig = inspect.signature(impl.__init__)
        hints = get_type_hints(impl.__init__)
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = hints.get(param_name)
            if param_type and param_type.__name__ in self._registrations:
                kwargs[param_name] = self.resolve(param_type)
            elif param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default
        return impl(**kwargs)

    def inject(self, func: Callable = None, **named_deps):
        """
        从容器注入装饰器

        Args:
            func: 要注入的函数
            **named_deps: 命名依赖映射
        """
        def decorator(f):
            # 获取原始类型注解（不解析字符串注解，避免命名空间问题）
            hints = {}
            for pname, param in inspect.signature(f).parameters.items():
                if param.annotation is not inspect.Parameter.empty:
                    ann = param.annotation
                    if isinstance(ann, str):
                        # 字符串注解，尝试从函数全局命名空间解析
                        try:
                            ann = eval(ann, getattr(f, '__globals__', {}))
                        except Exception:
                            pass
                    hints[pname] = ann
            sig = inspect.signature(f)

            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                for param_name, param_type in hints.items():
                    if param_name in kwargs:
                        continue
                    if param_type:
                        if param_name in named_deps:
                            kwargs[param_name] = named_deps[param_name]
                        elif hasattr(param_type, '__name__') and param_type.__name__ in self._registrations:
                            kwargs[param_name] = self.resolve(param_type)
                return f(*args, **kwargs)
            # 清除注解和 __wrapped__，设置空签名，避免 FastAPI 将注入参数当作请求/响应模型
            wrapper.__annotations__ = {}
            if hasattr(wrapper, '__wrapped__'):
                delattr(wrapper, '__wrapped__')
            wrapper.__signature__ = inspect.Signature()
            return wrapper

        if func:
            return decorator(func)
        return decorator

    def clear_scoped(self):
        self._scoped.clear()

    def clear_all(self):
        self._registrations.clear()
        self._singletons.clear()
        self._scoped.clear()


# 全局容器（使用 oven 存储确保单例，避免重复导入创建多个实例）
if "container" in oven.muffin_sugar:
    container = oven.muffin_sugar["container"]
else:
    container = IoCContainer()


def inject(func: Callable = None, **named_deps):
    """全局注入装饰器快捷方式"""
    return container.inject(func, **named_deps)


# 注册到 oven，使 embed 自动注入到 builtins
oven.muffin_flour["auto_inject"] = auto_inject
oven.muffin_flour["inject"] = inject
oven.muffin_water["IoCContainer"] = IoCContainer
oven.muffin_water["Scope"] = Scope
oven.muffin_sugar["container"] = container
