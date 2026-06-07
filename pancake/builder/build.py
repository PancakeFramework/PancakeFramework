"""构建模块 — 使用 DoughFactory 创建和启动所有 Bean"""

import logging
from pancake.factory.dough_factory import DoughFactory

logger = logging.getLogger(__name__)


def build():
    """创建所有 Bean 并启动（同步版本，仅适用于纯同步生命周期）"""
    factory = DoughFactory.get()
    factory.create_all()
    factory.startup_all()


async def async_build():
    """创建所有 Bean 并启动（异步版本，支持 async 生命周期）"""
    factory = DoughFactory.get()
    await factory.async_create_all()
    await factory.async_startup_all()
