"""
MyBatis Plus 异步持久化模块
模仿 MyBatis Plus 核心功能：
- BaseMapper: 内置 CRUD (select_by_id, select_list, insert, update_by_id, delete_by_id...)
- @Mapper: 标记 Mapper 类，自动继承 BaseMapper
- @Select/@Insert/@Update/@Delete: 自定义 SQL 注解
- #{param} 参数绑定 + 动态 SQL
- dataclass 实体映射
- 零 import 使用（由 embed.py 自动注入 builtins）
"""

import logging
from dataclasses import dataclass

from .mapper import (
    Mapper, BaseMapper, Select, SelectOne, Insert, Update, Delete,
    get_registered_mappers,
)
from .wrapper import QueryWrapper, UpdateWrapper, ColumnRef, qw, uw, entity_columns
from .connection import init_database, close_database, get_database
from .config import load_config

logger = logging.getLogger(__name__)


# 装饰器定义在子模块中，load_dlc 的 __module__ 过滤无法识别，需手动注册到 muffin_flour
# embed.py 会自动将 muffin_flour 中的所有项注入 builtins
from pancake import oven
oven.muffin_flour["Mapper"] = Mapper
oven.muffin_flour["BaseMapper"] = BaseMapper
oven.muffin_flour["Select"] = Select
oven.muffin_flour["SelectOne"] = SelectOne
oven.muffin_flour["Insert"] = Insert
oven.muffin_flour["Update"] = Update
oven.muffin_flour["Delete"] = Delete
oven.muffin_flour["dataclass"] = dataclass
oven.muffin_flour["qw"] = qw
oven.muffin_flour["uw"] = uw
oven.muffin_flour["UpdateWrapper"] = UpdateWrapper
oven.muffin_flour["QueryWrapper"] = QueryWrapper
oven.muffin_flour["ColumnRef"] = ColumnRef
oven.muffin_flour["entity_columns"] = entity_columns

# 注册分页相关类
from .mapper import Page, PageResult
oven.muffin_flour["Page"] = Page
oven.muffin_flour["PageResult"] = PageResult


class Main(InitAction):

    init_order = 1  # 在 embed 之后，web 之前

    def __init__(self):
        self.config = load_config()

    @staticmethod
    def check():
        from pancake import oven
        url = oven.pancake_yaml.get("mybatis.database.url")
        if url is None:
            logger.warning("未配置 mybatis.database.url，使用默认 SQLite")

    async def _init_db(self):
        await init_database(
            url=self.config["url"],
            min_size=self.config.get("min_size", 1),
            max_size=self.config.get("max_size", 5),
        )

    def build(self):
        # 注册 startup/shutdown 钩子，在 uvicorn event loop 中执行
        oven.muffin_egg.setdefault("on_startup", []).append(self._init_db)
        oven.muffin_egg.setdefault("on_shutdown", []).append(self.shutdown)
        logger.info("MyBatis Plus 模块构建完成")

    async def shutdown(self):
        await close_database()


__all__ = [
    "Mapper", "BaseMapper", "Select", "SelectOne", "Insert", "Update", "Delete",
    "QueryWrapper", "UpdateWrapper", "ColumnRef", "qw", "uw", "entity_columns",
    "get_database", "init_database", "close_database",
]
