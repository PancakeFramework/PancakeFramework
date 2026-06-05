"""DatabaseManager 测试"""

import pytest
import asyncio
from pancake_mybatis.connection import DatabaseManager, create_manager


class TestDatabaseManager:

    def test_create_manager(self):
        manager = DatabaseManager()
        assert manager._database is None

    def test_get_before_init_raises(self):
        manager = DatabaseManager()
        with pytest.raises(RuntimeError, match="未初始化"):
            manager.get()

    def test_reset(self):
        manager = DatabaseManager()
        manager._database = "fake"
        manager.reset()
        assert manager._database is None

    def test_create_manager_factory(self):
        m1 = create_manager()
        m2 = create_manager()
        assert m1 is not m2

    @pytest.mark.asyncio
    async def test_sqlite_connect_and_close(self):
        manager = DatabaseManager()
        db = await manager.init("sqlite:///test_temp.db")
        assert db is not None
        assert manager.get() is db
        await manager.close()
        assert manager._database is None
        # cleanup
        import os
        if os.path.exists("test_temp.db"):
            os.remove("test_temp.db")

    @pytest.mark.asyncio
    async def test_sqlite_creates_directory(self, tmp_path):
        db_path = tmp_path / "subdir" / "app.db"
        manager = DatabaseManager()
        db = await manager.init(f"sqlite:///{db_path}")
        assert db is not None
        await manager.close()

    def test_backward_compat_module_functions(self):
        """模块级函数仍然可用"""
        from pancake.ovenware.mybatis.connection import init_database, close_database, get_database
        assert callable(init_database)
        assert callable(close_database)
        assert callable(get_database)
