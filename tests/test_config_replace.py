"""测试配置热重载清理旧配置

验证 settings.replace() 会清除旧的 key，
settings.init() 只做 merge。
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pancake import settings


def test_init_merges():
    """init 只做 merge，不删除旧 key"""
    settings.reset()

    settings.init({"a": 1, "b": 2})
    assert settings.get("a") == 1
    assert settings.get("b") == 2

    settings.init({"b": 20, "c": 3})
    assert settings.get("a") == 1  # 旧 key 保留
    assert settings.get("b") == 20  # 更新
    assert settings.get("c") == 3  # 新 key

    print("[OK] init 只做 merge，旧 key 保留")


def test_replace_clears_old():
    """replace 清除旧配置，只保留新配置"""
    settings.reset()

    settings.init({"a": 1, "b": 2, "c": 3})
    assert settings.get("a") == 1
    assert settings.get("b") == 2
    assert settings.get("c") == 3

    # replace 后 b 被删除
    settings.replace({"a": 10, "c": 30})
    assert settings.get("a") == 10  # 更新
    assert settings.get("b") is None  # 已删除
    assert settings.get("c") == 30  # 更新

    print("[OK] replace 清除旧配置")


def test_replace_empty():
    """replace 空字典清空所有用户配置"""
    settings.reset()

    settings.init({"a": 1, "b": 2})
    settings.replace({})
    assert settings.get("a") is None
    assert settings.get("b") is None

    print("[OK] replace 空字典清空所有配置")


def test_replace_none():
    """replace None 清空所有用户配置"""
    settings.reset()

    settings.init({"a": 1})
    settings.replace(None)
    assert settings.get("a") is None

    print("[OK] replace None 清空所有配置")


def test_defaults_preserved():
    """replace 不影响通过 init 设置的配置"""
    settings.reset()

    # 模拟 XML 加载的配置（paths.src_dir 现在是 _DEFAULTS 内置值，始终可用）
    settings.init({"pancake.title": "Test App"})
    settings.init({"custom_key": "value"})
    settings.replace({"new_key": "new"})

    # replace 清除了用户配置，但 _DEFAULTS 中的值仍然可用
    assert settings.get("custom_key") is None
    assert settings.get("paths.src_dir") == "src"  # _DEFAULTS 内置默认值
    assert settings.get("new_key") == "new"

    print("[OK] replace 清除用户配置，保留内置默认值")


if __name__ == "__main__":
    test_init_merges()
    test_replace_clears_old()
    test_replace_empty()
    test_replace_none()
    test_defaults_preserved()
    print("\n所有测试通过！")
