"""
MyBatis Plus 风格链式条件构造器
- QueryWrapper: 查询条件构造
- UpdateWrapper: 更新条件构造
- qw(): 快捷工厂函数
"""

import re
from typing import Any

_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _resolve_column(column) -> str:
    """解析列名，支持字符串和 ColumnRef"""
    if isinstance(column, str):
        if not _IDENTIFIER_RE.match(column):
            raise ValueError(f"Invalid column name: {column!r}")
        return column
    if hasattr(column, '_column_name'):
        return column._column_name
    raise TypeError(f"列名必须是字符串或 ColumnRef，得到 {type(column)}")


class ColumnRef:
    """列引用，用于 Lambda 风格"""

    def __init__(self, name: str):
        self._column_name = name

    def __repr__(self):
        return f"ColumnRef({self._column_name})"


def entity_columns(entity_cls) -> dict[str, ColumnRef]:
    """从 dataclass 实体类生成列引用字典"""
    from dataclasses import fields, is_dataclass
    if not is_dataclass(entity_cls):
        raise TypeError(f"{entity_cls} 不是 dataclass")
    return {f.name: ColumnRef(f.name) for f in fields(entity_cls)}


class QueryWrapper:
    """
    链式条件构造器，类似 MyBatis Plus QueryWrapper

    用法:
        qw().eq("name", "Alice").ge("age", 18).orderBy_desc("age")
        qw().like("name", "A").in_("status", [1, 2, 3]).limit(10)
    """

    def __init__(self):
        self._conditions: list[tuple[str, str, Any]] = []  # (column, op, value)
        self._order_by: list[tuple[str, str]] = []  # (column, direction)
        self._group_by: list[str] = []
        self._having: str = ""
        self._having_params: dict = {}
        self._limit: int | None = None
        self._offset: int | None = None
        self._select_cols: list[str] = []
        self._raw_sqls: list[tuple[str, dict]] = []  # (sql, params) 参数化原始 SQL 片段
        self._param_idx: int = 0
        self._or_groups: list = []  # 用于 OR 分组
        self._current_logic: str = "AND"

    def _next_param(self, column: str) -> str:
        self._param_idx += 1
        return f"__qw_{column}_{self._param_idx}"

    # ---- 比较条件 ----

    def eq(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "=", value))
        return self

    def ne(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "!=", value))
        return self

    def gt(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, ">", value))
        return self

    def ge(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, ">=", value))
        return self

    def lt(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "<", value))
        return self

    def le(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "<=", value))
        return self

    # ---- LIKE ----

    def like(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "LIKE", value))
        return self

    def not_like(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "NOT LIKE", value))
        return self

    def like_left(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "LIKE_LEFT", f"%{value}"))
        return self

    def like_right(self, column, value) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "LIKE_RIGHT", f"{value}%"))
        return self

    # ---- IN / NOT IN ----

    def in_(self, column, values: list) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "IN", values))
        return self

    def not_in(self, column, values: list) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "NOT IN", values))
        return self

    # ---- BETWEEN ----

    def between(self, column, low, high) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "BETWEEN", (low, high)))
        return self

    def not_between(self, column, low, high) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "NOT BETWEEN", (low, high)))
        return self

    # ---- NULL ----

    def is_null(self, column) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "IS NULL", None))
        return self

    def is_not_null(self, column) -> "QueryWrapper":
        column = _resolve_column(column)
        self._conditions.append((column, "IS NOT NULL", None))
        return self

    # ---- 逻辑分组 ----

    def and_(self, wrapper_fn) -> "QueryWrapper":
        """AND 嵌套条件: qw().eq("a", 1).and_(lambda w: w.eq("b", 2).or_.eq("c", 3))"""
        sub = QueryWrapper()
        wrapper_fn(sub)
        sql, params = sub._build_conditions()
        if sql:
            self._or_groups.append(("AND", sql, params))
        return self

    def or_(self, wrapper_fn) -> "QueryWrapper":
        """OR 嵌套条件: qw().eq("a", 1).or_(lambda w: w.eq("b", 2).eq("c", 3))"""
        sub = QueryWrapper()
        wrapper_fn(sub)
        sql, params = sub._build_conditions()
        if sql:
            self._or_groups.append(("OR", sql, params))
        return self

    def or_eq(self, column, value) -> "QueryWrapper":
        """OR 条件快捷方式"""
        column = _resolve_column(column)
        self._or_groups.append(("OR_INLINE", column, "=", value))
        return self

    # ---- 排序 / 分页 ----

    def order_by_asc(self, *columns) -> "QueryWrapper":
        for col in columns:
            self._order_by.append((_resolve_column(col), "ASC"))
        return self

    def order_by_desc(self, *columns) -> "QueryWrapper":
        for col in columns:
            self._order_by.append((_resolve_column(col), "DESC"))
        return self

    def group_by(self, *columns) -> "QueryWrapper":
        for col in columns:
            self._group_by.append(_resolve_column(col))
        return self

    def having(self, condition: str, params: dict = None) -> "QueryWrapper":
        """HAVING 条件（参数化）

        Args:
            condition: 条件表达式，使用 :name 参数占位符防注入
            params: 参数字典

        用法:
            qw().group_by("dept").having("COUNT(*) > :min_count", {"min_count": 5})
        """
        self._having = condition
        if params:
            self._having_params.update(params)
        return self

    def limit(self, n: int) -> "QueryWrapper":
        self._limit = n
        return self

    def offset(self, n: int) -> "QueryWrapper":
        self._offset = n
        return self

    def append_raw(self, sql: str, params: dict = None) -> "QueryWrapper":
        """追加参数化原始 SQL 片段

        Args:
            sql: SQL 片段，使用 :name 参数占位符
            params: 参数字典

        用法:
            qw().eq("status", 1).append_raw("age > :min_age", {"min_age": 18})
        """
        self._raw_sqls.append((sql, params or {}))
        return self

    def last(self, sql: str) -> "QueryWrapper":
        """追加原始 SQL 片段（已废弃，请使用 append_raw）

        .. deprecated:: 使用 append_raw(sql, params) 替代，避免 SQL 注入风险
        """
        import warnings
        warnings.warn(
            "last() 已废弃，有 SQL 注入风险，请使用 append_raw(sql, params)",
            DeprecationWarning,
            stacklevel=2,
        )
        self._raw_sqls.append((sql, {}))
        return self

    # ---- 列选择 ----

    def select_columns(self, *columns) -> "QueryWrapper":
        self._select_cols = [_resolve_column(c) for c in columns]
        return self

    # ---- 内部方法 ----

    def _build_conditions(self) -> tuple[str, dict]:
        """构建 WHERE 条件部分"""
        parts = []
        values = {}

        for column, op, value in self._conditions:
            if op == "IS NULL":
                parts.append(f"{column} IS NULL")
            elif op == "IS NOT NULL":
                parts.append(f"{column} IS NOT NULL")
            elif op == "IN":
                if not value:
                    parts.append("1 = 0")  # 空 IN 永远为 false
                    continue
                param_names = []
                for i, v in enumerate(value):
                    pname = f"__qw_{column}_in_{i}_{self._param_idx}"
                    self._param_idx += 1
                    param_names.append(f":{pname}")
                    values[pname] = v
                parts.append(f"{column} IN ({', '.join(param_names)})")
            elif op == "NOT IN":
                if not value:
                    continue
                param_names = []
                for i, v in enumerate(value):
                    pname = f"__qw_{column}_notin_{i}_{self._param_idx}"
                    self._param_idx += 1
                    param_names.append(f":{pname}")
                    values[pname] = v
                parts.append(f"{column} NOT IN ({', '.join(param_names)})")
            elif op == "BETWEEN":
                low, high = value
                p1 = self._next_param(column + "_low")
                p2 = self._next_param(column + "_high")
                parts.append(f"{column} BETWEEN :{p1} AND :{p2}")
                values[p1] = low
                values[p2] = high
            elif op == "NOT BETWEEN":
                low, high = value
                p1 = self._next_param(column + "_low")
                p2 = self._next_param(column + "_high")
                parts.append(f"{column} NOT BETWEEN :{p1} AND :{p2}")
                values[p1] = low
                values[p2] = high
            elif op in ("LIKE_LEFT", "LIKE_RIGHT", "LIKE", "NOT LIKE"):
                op_sql = "LIKE" if op != "NOT LIKE" else "NOT LIKE"
                pname = self._next_param(column)
                parts.append(f"{column} {op_sql} :{pname}")
                values[pname] = value
            else:
                pname = self._next_param(column)
                parts.append(f"{column} {op} :{pname}")
                values[pname] = value

        # 处理 OR 分组（包含 and_/or_ 嵌套和 or_eq 快捷方式）
        or_parts = []
        for group in self._or_groups:
            if group[0] == "OR_INLINE":
                _, column, op, value = group
                pname = self._next_param(column)
                or_parts.append(f"{column} {op} :{pname}")
                values[pname] = value
            elif group[0] in ("AND", "OR"):
                logic, sub_sql, sub_params = group
                if logic == "OR":
                    or_parts.append(sub_sql)
                else:
                    parts.append(f"({sub_sql})")
                values.update(sub_params)

        and_where = " AND ".join(parts)
        if or_parts:
            or_where = " OR ".join(or_parts)
            if and_where:
                where = f"({and_where}) OR ({or_where})"
            else:
                where = f"({or_where})"
        else:
            where = and_where
        return where, values

    def to_where_clause(self) -> tuple[str, dict]:
        """生成 WHERE 子句"""
        where, values = self._build_conditions()
        if where:
            return f" WHERE {where}", values
        return "", values

    def to_select_sql(self, table_name: str) -> tuple[str, dict]:
        """生成完整 SELECT SQL"""
        cols = ", ".join(self._select_cols) if self._select_cols else "*"
        where_clause, values = self.to_where_clause()

        sql = f"SELECT {cols} FROM {table_name}{where_clause}"

        if self._group_by:
            sql += f" GROUP BY {', '.join(self._group_by)}"
        if self._having:
            sql += f" HAVING {self._having}"
            values.update(self._having_params)
        if self._order_by:
            order_parts = [f"{col} {dir}" for col, dir in self._order_by]
            sql += f" ORDER BY {', '.join(order_parts)}"
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        for raw_sql, raw_params in self._raw_sqls:
            sql += f" {raw_sql}"
            values.update(raw_params)

        return sql, values

    def to_count_sql(self, table_name: str) -> tuple[str, dict]:
        """生成 COUNT SQL"""
        where_clause, values = self.to_where_clause()
        sql = f"SELECT COUNT(*) as cnt FROM {table_name}{where_clause}"
        if self._group_by:
            sql += f" GROUP BY {', '.join(self._group_by)}"
        if self._having:
            sql += f" HAVING {self._having}"
            values.update(self._having_params)
        return sql, values

    # ---- 向后兼容 camelCase 别名 ----

    notLike = not_like
    likeLeft = like_left
    likeRight = like_right
    notIn = not_in
    notBetween = not_between
    isNull = is_null
    isNotNull = is_not_null
    orderByAsc = order_by_asc
    orderByDesc = order_by_desc
    groupBy = group_by


class UpdateWrapper(QueryWrapper):
    """
    链式更新构造器，继承 QueryWrapper 的条件方法

    用法:
        UpdateWrapper().set("name", "Bob").set("age", 20).eq("id", 1)
    """

    def __init__(self):
        super().__init__()
        self._set_clauses: list[tuple[str, Any]] = []

    def set(self, column, value) -> "UpdateWrapper":
        """SET column = value"""
        column = _resolve_column(column)
        self._set_clauses.append((column, value))
        return self

    def to_update_sql(self, table_name: str) -> tuple[str, dict]:
        """生成完整 UPDATE SQL"""
        if not self._set_clauses:
            raise ValueError("UpdateWrapper 必须至少有一个 set() 调用")

        values = {}
        set_parts = []
        for column, value in self._set_clauses:
            pname = self._next_param(column)
            set_parts.append(f"{column} = :{pname}")
            values[pname] = value

        where_clause, where_values = self.to_where_clause()
        values.update(where_values)

        sql = f"UPDATE {table_name} SET {', '.join(set_parts)}{where_clause}"
        return sql, values

    def to_delete_sql(self, table_name: str) -> tuple[str, dict]:
        """生成 DELETE SQL（复用条件部分）"""
        where_clause, values = self.to_where_clause()
        sql = f"DELETE FROM {table_name}{where_clause}"
        return sql, values


def qw() -> QueryWrapper:
    """快捷工厂函数，创建 QueryWrapper 实例"""
    return QueryWrapper()


def uw() -> UpdateWrapper:
    """快捷工厂函数，创建 UpdateWrapper 实例"""
    return UpdateWrapper()
