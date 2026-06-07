"""Service 基类"""

from pancake.dough import Dough


class Service(Dough):
    """服务类 — 方法集合

    类似 Spring @Service
    方法通过 @staticmethod 定义，通过 @inject 注入依赖
    """
    pass
