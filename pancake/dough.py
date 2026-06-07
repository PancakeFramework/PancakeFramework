"""
Dough 系统 — Bean 基类、元类、作用域
"""

from abc import ABCMeta
from enum import Enum


class Scope(Enum):
    """Bean 作用域"""
    SINGLETON = "singleton"  # 全局唯一（默认）
    PROTOTYPE = "prototype"  # 每次创建新实例
    LAZY = "lazy"           # 首次使用时创建


class DoughMeta(ABCMeta):
    """元类：自动注册类到全局注册表

    跳过名为 "Dough" 的类（基类自身）
    """
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "Dough":
            from pancake.registry import register_class
            register_class(name, cls)
        return cls
