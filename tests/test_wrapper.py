"""QueryWrapper / UpdateWrapper 链式查询测试"""

import pytest
from pancake_mybatis.wrapper import QueryWrapper, UpdateWrapper, qw, uw, ColumnRef, _resolve_column


class TestResolveColumn:

    def test_string_column(self):
        assert _resolve_column("name") == "name"

    def test_column_ref(self):
        ref = ColumnRef("age")
        assert _resolve_column(ref) == "age"

    def test_invalid_column(self):
        with pytest.raises(ValueError):
            _resolve_column("name; DROP TABLE")

    def test_invalid_type(self):
        with pytest.raises(TypeError):
            _resolve_column(123)


class TestQueryWrapperBasicConditions:

    def test_eq(self):
        sql, params = qw().eq("name", "Alice").to_select_sql("users")
        assert "name = :__qw_name_1" in sql
        assert params["__qw_name_1"] == "Alice"

    def test_ne(self):
        sql, params = qw().ne("name", "Bob").to_select_sql("users")
        assert "name != :__qw_name_1" in sql

    def test_gt(self):
        sql, params = qw().gt("age", 18).to_select_sql("users")
        assert "age > :__qw_age_1" in sql

    def test_ge(self):
        sql, params = qw().ge("age", 18).to_select_sql("users")
        assert "age >= :__qw_age_1" in sql

    def test_lt(self):
        sql, params = qw().lt("age", 18).to_select_sql("users")
        assert "age < :__qw_age_1" in sql

    def test_le(self):
        sql, params = qw().le("age", 18).to_select_sql("users")
        assert "age <= :__qw_age_1" in sql


class TestQueryWrapperLike:

    def test_like(self):
        sql, params = qw().like("name", "Ali").to_select_sql("users")
        assert "name LIKE :__qw_name_1" in sql
        assert params["__qw_name_1"] == "Ali"

    def test_not_like(self):
        sql, params = qw().notLike("name", "Bob").to_select_sql("users")
        assert "name NOT LIKE :__qw_name_1" in sql

    def test_like_left(self):
        sql, params = qw().likeLeft("name", "ice").to_select_sql("users")
        assert params["__qw_name_1"] == "%ice"

    def test_like_right(self):
        sql, params = qw().likeRight("name", "Ali").to_select_sql("users")
        assert params["__qw_name_1"] == "Ali%"


class TestQueryWrapperInBetween:

    def test_in(self):
        sql, params = qw().in_("status", [1, 2, 3]).to_select_sql("users")
        assert "status IN (" in sql
        assert len([k for k in params if k.startswith("__qw_status_in")]) == 3

    def test_not_in(self):
        sql, params = qw().notIn("status", [1, 2]).to_select_sql("users")
        assert "status NOT IN (" in sql

    def test_in_empty(self):
        sql, params = qw().in_("status", []).to_select_sql("users")
        assert "1 = 0" in sql

    def test_between(self):
        sql, params = qw().between("age", 18, 30).to_select_sql("users")
        assert "age BETWEEN :__qw_age_low_1 AND :__qw_age_high_2" in sql

    def test_not_between(self):
        sql, params = qw().notBetween("age", 18, 30).to_select_sql("users")
        assert "age NOT BETWEEN" in sql


class TestQueryWrapperNull:

    def test_is_null(self):
        sql, params = qw().isNull("name").to_select_sql("users")
        assert "name IS NULL" in sql
        assert params == {}

    def test_is_not_null(self):
        sql, params = qw().isNotNull("name").to_select_sql("users")
        assert "name IS NOT NULL" in sql


class TestQueryWrapperOrderBy:

    def test_order_by_asc(self):
        sql, _ = qw().orderByAsc("name").to_select_sql("users")
        assert "ORDER BY name ASC" in sql

    def test_order_by_desc(self):
        sql, _ = qw().orderByDesc("age").to_select_sql("users")
        assert "ORDER BY age DESC" in sql

    def test_multiple_order_by(self):
        sql, _ = qw().orderByAsc("name").orderByDesc("age").to_select_sql("users")
        assert "ORDER BY name ASC, age DESC" in sql


class TestQueryWrapperGroupByHaving:

    def test_group_by(self):
        sql, _ = qw().groupBy("dept").to_select_sql("users")
        assert "GROUP BY dept" in sql

    def test_having(self):
        sql, params = qw().groupBy("dept").having("COUNT(*) > :cnt", {"cnt": 5}).to_select_sql("users")
        assert "HAVING COUNT(*) > :cnt" in sql


class TestQueryWrapperLimitOffset:

    def test_limit(self):
        sql, _ = qw().limit(10).to_select_sql("users")
        assert "LIMIT 10" in sql

    def test_offset(self):
        sql, _ = qw().limit(10).offset(20).to_select_sql("users")
        assert "LIMIT 10" in sql
        assert "OFFSET 20" in sql


class TestQueryWrapperSelectColumns:

    def test_select_columns(self):
        sql, _ = qw().select_columns("name", "age").to_select_sql("users")
        assert "SELECT name, age FROM" in sql

    def test_select_all(self):
        sql, _ = qw().to_select_sql("users")
        assert "SELECT * FROM" in sql


class TestQueryWrapperCompoundConditions:

    def test_and_conditions(self):
        sql, params = qw().eq("name", "Alice").ge("age", 18).to_select_sql("users")
        assert "name = :__qw_name_1" in sql
        assert "age >= :__qw_age_2" in sql
        assert " AND " in sql

    def test_or_eq(self):
        sql, params = qw().eq("a", 1).or_eq("b", 2).to_select_sql("t")
        assert " OR " in sql

    def test_and_nested(self):
        sql, params = qw().eq("a", 1).and_(lambda w: w.eq("b", 2).eq("c", 3)).to_select_sql("t")
        assert "a = :__qw_a_1" in sql

    def test_or_nested(self):
        sql, params = qw().eq("a", 1).or_(lambda w: w.eq("b", 2).eq("c", 3)).to_select_sql("t")
        assert " OR " in sql


class TestQueryWrapperCount:

    def test_count_sql(self):
        sql, params = qw().eq("active", True).to_count_sql("users")
        assert sql.startswith("SELECT COUNT(*) as cnt FROM users")
        assert "active = :__qw_active_1" in sql


class TestUpdateWrapper:

    def test_set_eq(self):
        sql, params = UpdateWrapper().set("name", "Bob").eq("id", 1).to_update_sql("users")
        assert "UPDATE users SET name = :__qw_name_1" in sql
        assert "id = :__qw_id_2" in sql

    def test_multiple_set(self):
        sql, params = UpdateWrapper().set("name", "Bob").set("age", 20).to_update_sql("users")
        assert "name = :__qw_name_1" in sql
        assert "age = :__qw_age_2" in sql

    def test_no_set_raises(self):
        with pytest.raises(ValueError):
            UpdateWrapper().eq("id", 1).to_update_sql("users")

    def test_delete_sql(self):
        sql, params = UpdateWrapper().eq("id", 1).to_delete_sql("users")
        assert "DELETE FROM users" in sql
        assert "id = :__qw_id_1" in sql


class TestFactoryFunctions:

    def test_qw(self):
        w = qw()
        assert isinstance(w, QueryWrapper)

    def test_uw(self):
        w = uw()
        assert isinstance(w, UpdateWrapper)
