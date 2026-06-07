"""测试 muffin_suger 拼写错误的 deprecation warning"""

import os
import sys
import warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_muffin_sugar_works():
    """muffin_sugar 正确拼写正常工作"""
    from pancake.oven.muffin import muffin_sugar
    muffin_sugar["test_key"] = "test_value"
    assert muffin_sugar["test_key"] == "test_value"
    muffin_sugar.pop("test_key", None)
    print("[OK] muffin_sugar 正常工作")


def test_muffin_suger_deprecation():
    """muffin_suger 旧拼写触发 deprecation warning"""
    from pancake.oven.muffin import muffin_suger

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # 访问时应该触发警告
        _ = muffin_suger.items()

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "muffin_suger" in str(w[0].message)
        assert "muffin_sugar" in str(w[0].message)
        print("[OK] muffin_suger 触发 DeprecationWarning")


def test_muffin_suger_still_works():
    """muffin_suger 旧拼写仍可使用（兼容）"""
    from pancake.oven.muffin import muffin_suger, muffin_sugar

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # 暂时忽略警告
        muffin_suger["compat_test"] = 42
        assert muffin_sugar["compat_test"] == 42  # 底层是同一个 dict
        muffin_sugar.pop("compat_test", None)
    print("[OK] muffin_suger 兼容性正常（底层同一 dict）")


if __name__ == "__main__":
    test_muffin_sugar_works()
    test_muffin_suger_deprecation()
    test_muffin_suger_still_works()
    print("\n所有测试通过！")
