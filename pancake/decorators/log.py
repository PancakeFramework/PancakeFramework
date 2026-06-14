"""日志装饰器 — @log（类似 Lombok @Slf4j）"""

import logging
from pancake.registry import export


@export
def log(cls):
    """@log — 自动为类注入 logger 实例

    注入的 logger 名称为 {module}.{qualname}，
    所有实例共享同一个 logger（模块级）。

    Usage:
        @log
        @service
        class MyService:
            async def on_init(self):
                self.logger.info("服务启动")
    """
    cls.logger = logging.getLogger(f"{cls.__module__}.{cls.__qualname__}")
    return cls
