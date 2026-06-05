"""Mapper 层测试"""

import pytest
from dataclasses import dataclass
from pancake_mybatis.mapper import (
    _validate_identifier, _get_table_name, _row_to_entity,
    _build_where_from_dict, BaseMapper, Mapper, get_registered_mappers,
)


class TestValidateIdentifier:

    def test_valid_identifiers(self):
        assert _validate_identifier("users") == "users"
        assert _validate_identifier("_private") == "_private"
        assert _validate_identifier("col123") == "col123"

    def test_injection_attempt(self):
        with pytest.raises(ValueError):
            _validate_identifier("users; DROP TABLE")
        with pytest.raises(ValueError):
            _validate_identifier("users OR 1=1")
        with pytest.raises(ValueError):
            _validate_identifier("")


class TestGetTableName:

    def test_mapper_suffix(self):
        assert _get_table_name(type("UserMapper", (), {})) == "user"

    def test_camel_case(self):
        assert _get_table_name(type("UserInfo", (), {})) == "user_info"

    def test_multi_word(self):
        assert _get_table_name(type("OrderItemMapper", (), {})) == "order_item"


class TestRowToEntity:

    def test_row_to_dataclass(self):
        @dataclass
        class User:
            id: int = None
            name: str = None

        row = {"id": 1, "name": "Alice", "extra": "ignored"}
        result = _row_to_entity(row, User)
        assert result.id == 1
        assert result.name == "Alice"

    def test_none_row(self):
        @dataclass
        class User:
            id: int = None

        assert _row_to_entity(None, User) is None

    def test_row_with_mapping(self):
        """模拟数据库 Row 对象"""
        @dataclass
        class User:
            id: int = None

        class FakeRow:
            _mapping = {"id": 42}

        result = _row_to_entity(FakeRow(), User)
        assert result.id == 42


class TestBuildWhereFromDict:

    def test_simple_where(self):
        where, values = _build_where_from_dict({"name": "Alice", "age": 20})
        assert "WHERE" in where
        assert "name = :name" in where
        assert "age = :age" in where
        assert values == {"name": "Alice", "age": 20}

    def test_none_values_skipped(self):
        where, values = _build_where_from_dict({"name": "Alice", "age": None})
        assert "name = :name" in where
        assert "age" not in where
        assert "age" not in values

    def test_empty_dict(self):
        where, values = _build_where_from_dict({})
        assert where == ""
        assert values == {}


class TestBaseMapper:

    @pytest.fixture
    def user_mapper(self):
        @dataclass
        class User:
            id: int = None
            name: str = None
            age: int = None

        class UserMapper(BaseMapper):
            _entity_class = User
            _table_name = "users"

        return UserMapper()

    def test_table_name_set(self, user_mapper):
        assert user_mapper._table_name == "users"

    def test_entity_class_set(self, user_mapper):
        assert user_mapper._entity_class is not None

    def test_type_map(self, user_mapper):
        assert user_mapper._TYPE_MAP[int] == "INTEGER"
        assert user_mapper._TYPE_MAP[str] == "TEXT"
        assert user_mapper._TYPE_MAP[float] == "REAL"
        assert user_mapper._TYPE_MAP[bool] == "INTEGER"


class TestMapperDecorator:

    def test_mapper_registers_class(self):
        from pancake import oven
        old_dough = dict(oven.pancake_dough)

        @Mapper
        class ProductMapper:
            @dataclass
            class Product:
                id: int = None
                title: str = None

            _entity_class = Product

        registered = get_registered_mappers()
        assert "ProductMapper" in registered

    def test_mapper_infers_table_name(self):
        @Mapper
        class OrderItemMapper:
            pass

        assert OrderItemMapper._table_name == "order_item"


class TestBaseMapperSqlGeneration:

    def test_select_by_id_sql(self, user_mapper=None):
        """验证 select_by_id 生成的 SQL 格式"""
        # 由于需要真实数据库连接，这里只验证方法存在
        assert hasattr(BaseMapper, "select_by_id")
        assert hasattr(BaseMapper, "select_list")
        assert hasattr(BaseMapper, "insert")
        assert hasattr(BaseMapper, "update_by_id")
        assert hasattr(BaseMapper, "delete_by_id")
        assert hasattr(BaseMapper, "select")
        assert hasattr(BaseMapper, "select_count")
        assert hasattr(BaseMapper, "insert_batch")
        assert hasattr(BaseMapper, "delete_batch_by_ids")
