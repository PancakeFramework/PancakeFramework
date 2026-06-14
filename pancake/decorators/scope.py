"""作用域装饰器 — @dough, @singleton, @prototype, @lazy"""

import warnings
from pancake.dough import Scope
from pancake.registry import export


def _check_scope_conflict(cls, new_scope):
    """检查类是否已设置不同的显式作用域，防止冲突

    @dough 设置的 SINGLETON 视为默认值，允许被覆盖。
    只在 @singleton/@prototype/@lazy 之间检测冲突。
    """
    existing = cls.__dict__.get('_scope')
    if not existing or existing == new_scope:
        return
    # @dough 只是标记，不阻止后续覆盖
    if cls.__dict__.get('_dough_only'):
        return
    raise TypeError(
        f"类 {cls.__name__} 已应用 @{existing.value} 作用域，"
        f"不能同时应用 @{new_scope.value} 作用域"
    )


@export
def dough(cls):
    """@dough — 标记类为 Bean（默认单例，允许被其他作用域覆盖）"""
    cls._scope = Scope.SINGLETON
    cls._dough_only = True
    return cls


@export
def singleton(cls):
    """@singleton — 单例作用域"""
    _check_scope_conflict(cls, Scope.SINGLETON)
    cls._scope = Scope.SINGLETON
    cls._dough_only = False
    return cls


@export
def prototype(cls):
    """@prototype — 每次获取创建新实例"""
    _check_scope_conflict(cls, Scope.PROTOTYPE)
    cls._scope = Scope.PROTOTYPE
    cls._dough_only = False
    return cls


@export
def lazy(cls):
    """@lazy — 延迟初始化"""
    _check_scope_conflict(cls, Scope.LAZY)
    cls._scope = Scope.LAZY
    cls._lazy = True
    cls._dough_only = False
    return cls
