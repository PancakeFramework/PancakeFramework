"""Decorators — 框架装饰器包

统一导出所有装饰器，保持 from pancake.decorators import xxx 兼容。
"""

from pancake.decorators.scope import dough, singleton, prototype, lazy
from pancake.decorators.bean import maker, maker_name, no_maker
from pancake.decorators.inject import inject, inject_name, _InjectName
from pancake.decorators.config import config, depends_on, import_class
from pancake.decorators.convert import service, configuration, function, struct
from pancake.decorators.log import log

__all__ = [
    # 作用域
    "dough", "singleton", "prototype", "lazy",
    # Bean 方法
    "maker", "maker_name", "no_maker",
    # 注入
    "inject", "inject_name",
    # 配置与依赖
    "config", "depends_on", "import_class",
    # 类型转换
    "service", "configuration", "function", "struct",
    # 日志
    "log",
]
