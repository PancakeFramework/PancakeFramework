import functools
import inspect
import logging
from pancake import oven
from .inject import auto_inject

logger = logging.getLogger(__name__)

# 确保 Service 注册表存在
oven.pancake_dough.setdefault("Service", {})
oven.pancake_pie.setdefault("Service", {})

"""
    服务装饰器
"""
class Service:
    _load_priority = 20  # Service 先于 controller (50) 加载

    def __init__(self, cls):

        cls.__init__ = auto_inject()(cls.__init__)

        def build(cls_, *args, **kwargs):
            return cls_(*args, **kwargs)

        build = functools.wraps(cls)(build)

        setattr(cls, 'build', classmethod(build))

        self.cls = cls

        oven.pancake_dough["Service"][self.cls.__name__] = cls
        logger.info(f"Service {self.cls.__name__} 已加入库")

    def __call__(self, *args, **kwargs):
        stack = inspect.stack()
        caller_method = stack[1].function if len(stack) > 1 else ""

        if caller_method not in ["build", "create"]:
            logger.info(f"Service {self.cls.__name__} 已调用, 这是不推荐的用法, 请使用 auto_inject")

        return self.cls(*args, **kwargs)

    def __str__(self):
        return self.cls.__name__

    @staticmethod
    def create(cls: str, name: str = None):
        service = oven.pancake_dough["Service"][cls]()
        if name is not None:
            oven.pancake_pie["Service"][name] = service
        return service

    @staticmethod
    def get(cls: str):
        return oven.pancake_pie["Service"][cls]


# 注册到 muffin_flour，使其被 embed 自动注入到 builtins
oven.muffin_flour["Service"] = Service