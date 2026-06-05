"""SQL 解析器测试"""

import pytest
from pancake_mybatis.sql_parser import parse_sql, _eval_test


class TestEvalTest:

    def test_truthy_variable(self):
        assert _eval_test("name", {"name": "Alice"}) is True
        assert _eval_test("name", {}) is False
        assert _eval_test("name", {"name": ""}) is False
        assert _eval_test("name", {"name": None}) is False

    def test_not_null(self):
        assert _eval_test("name != null", {"name": "Alice"}) is True
        assert _eval_test("name != null", {"name": None}) is False

    def test_eq_null(self):
        assert _eval_test("name == null", {"name": None}) is True
        assert _eval_test("name == null", {"name": "Alice"}) is False

    def test_not_empty_string(self):
        assert _eval_test("name != ''", {"name": "Alice"}) is True
        assert _eval_test("name != ''", {"name": ""}) is False
        assert _eval_test("name != ''", {"name": None}) is False

    def test_eq_empty_string(self):
        assert _eval_test("name == ''", {"name": ""}) is True
        assert _eval_test("name == ''", {"name": None}) is True
        assert _eval_test("name == ''", {"name": "Alice"}) is False

    def test_comparison_operators(self):
        assert _eval_test("age > 18", {"age": 20}) is True
        assert _eval_test("age > 18", {"age": 16}) is False
        assert _eval_test("age >= 18", {"age": 18}) is True
        assert _eval_test("age < 18", {"age": 16}) is True
        assert _eval_test("age <= 18", {"age": 18}) is True
        assert _eval_test("age != 18", {"age": 20}) is True

    def test_and_logic(self):
        assert _eval_test("age > 18 and name != null", {"age": 20, "name": "A"}) is True
        assert _eval_test("age > 18 and name != null", {"age": 20, "name": None}) is False

    def test_or_logic(self):
        assert _eval_test("age > 18 or name != null", {"age": 16, "name": "A"}) is True
        assert _eval_test("age > 18 or name != null", {"age": 16, "name": None}) is False


class TestParamBinding:

    def test_simple_binding(self):
        sql = "SELECT * FROM users WHERE name = #{name}"
        parsed, params = parse_sql(sql, {"name": "Alice"})
        assert ":name" in parsed
        assert "#{name}" not in parsed
        assert params["name"] == "Alice"

    def test_multiple_params(self):
        sql = "SELECT * FROM users WHERE name = #{name} AND age = #{age}"
        parsed, params = parse_sql(sql, {"name": "Alice", "age": 20})
        assert ":name" in parsed
        assert ":age" in parsed
        assert params == {"name": "Alice", "age": 20}


class TestIfTag:

    def test_if_true(self):
        sql = "SELECT * FROM users <if test=\"name != null\">WHERE name = #{name}</if>"
        parsed, params = parse_sql(sql, {"name": "Alice"})
        assert "WHERE name = :name" in parsed
        assert params["name"] == "Alice"

    def test_if_false(self):
        sql = "SELECT * FROM users <if test=\"name != null\">WHERE name = #{name}</if>"
        parsed, params = parse_sql(sql, {"name": None})
        assert "WHERE" not in parsed
        assert "name" not in params

    def test_if_with_truthy(self):
        sql = "SELECT * FROM users <if test=\"name\">WHERE name = #{name}</if>"
        parsed, params = parse_sql(sql, {"name": "Alice"})
        assert "WHERE name = :name" in parsed


class TestWhereTag:

    def test_where_strips_leading_and(self):
        sql = "SELECT * FROM users <where>AND name = #{name}</where>"
        parsed, params = parse_sql(sql, {"name": "Alice"})
        assert parsed.startswith("SELECT * FROM users WHERE")
        assert "AND" not in parsed.split("WHERE")[1].lstrip()

    def test_where_empty(self):
        sql = "SELECT * FROM users <where></where>"
        parsed, params = parse_sql(sql, {})
        assert "WHERE" not in parsed


class TestSetTag:

    def test_set_strips_trailing_comma(self):
        sql = "UPDATE users <set>name = #{name},</set> WHERE id = #{id}"
        parsed, params = parse_sql(sql, {"name": "Alice", "id": 1})
        assert "SET name = :name" in parsed
        assert parsed.rstrip().endswith("WHERE id = :id") or "WHERE id = :id" in parsed

    def test_set_empty(self):
        sql = "UPDATE users <set></set> WHERE id = #{id}"
        parsed, params = parse_sql(sql, {"id": 1})
        assert "SET" not in parsed


class TestForeachTag:

    def test_foreach_basic(self):
        sql = "SELECT * FROM users WHERE id IN <foreach collection=\"ids\" item=\"id\" open=\"(\" close=\")\" separator=\",\">#{id}</foreach>"
        parsed, params = parse_sql(sql, {"ids": [1, 2, 3]})
        assert "IN (" in parsed
        assert parsed.count(":__foreach_ids_") == 3

    def test_foreach_empty(self):
        sql = "SELECT * FROM users WHERE id IN <foreach collection=\"ids\" item=\"id\" open=\"(\" close=\")\" separator=\",\">#{id}</foreach>"
        parsed, params = parse_sql(sql, {"ids": []})
        # 空集合时 foreach 内容为空，但 IN 关键字在静态部分
        # 实际行为: "WHERE id IN " (无括号内容)
        assert "(" not in parsed  # 没有生成括号内容


class TestChooseTag:

    def test_choose_when_match(self):
        sql = """SELECT * FROM users
            <choose>
                <when test="name != null">WHERE name = #{name}</when>
                <otherwise>WHERE 1 = 1</otherwise>
            </choose>"""
        parsed, params = parse_sql(sql, {"name": "Alice"})
        assert "WHERE name = :name" in parsed

    def test_choose_otherwise(self):
        sql = """SELECT * FROM users
            <choose>
                <when test="name != null">WHERE name = #{name}</when>
                <otherwise>WHERE 1 = 1</otherwise>
            </choose>"""
        parsed, params = parse_sql(sql, {"name": None})
        assert "WHERE 1 = 1" in parsed


class TestUnusedParamFilter:

    def test_filters_unused(self):
        sql = "SELECT * FROM users WHERE name = #{name}"
        parsed, params = parse_sql(sql, {"name": "Alice", "unused": "value"})
        assert "unused" not in params
        assert params["name"] == "Alice"
