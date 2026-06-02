"""
异步数据库连接管理器
支持 SQLite / PostgreSQL / MySQL 等
"""

import logging
import os

from databases import Database

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库连接管理器 — 封装数据库连接状态

    使用方法:
        manager = DatabaseManager()
        await manager.init("sqlite:///app.db")
        db = manager.get()
        await manager.close()
    """

    def __init__(self):
        self._database: Database | None = None

    async def init(self, url: str, **kwargs) -> Database:
        """初始化数据库连接"""
        # SQLite: 确保目录存在，不传连接池参数
        if url.startswith("sqlite"):
            db_path = url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            kwargs.pop("min_size", None)
            kwargs.pop("max_size", None)

        self._database = Database(url, **kwargs)
        await self._database.connect()
        logger.info(f"数据库已连接: {url.split('@')[-1] if '@' in url else url}")
        return self._database

    async def close(self):
        """关闭数据库连接"""
        if self._database:
            await self._database.disconnect()
            logger.info("数据库已断开")
            self._database = None

    def get(self) -> Database:
        """获取当前数据库实例"""
        if self._database is None:
            raise RuntimeError("数据库未初始化，请先调用 init_database()")
        return self._database

    def reset(self):
        """重置状态（用于测试，不断开连接）"""
        self._database = None


# 向后兼容的模块级默认实例
_manager = DatabaseManager()

init_database = _manager.init
close_database = _manager.close
get_database = _manager.get


def create_manager() -> DatabaseManager:
    """创建新的独立管理器（用于测试）"""
    return DatabaseManager()
