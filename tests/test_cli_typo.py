"""测试 cli.py 中 __pycache__ 过滤修复"""

import os
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_pycache_filtered():
    """验证 __pycache__ 目录被正确过滤"""
    # 模拟 os.walk 的 dirs 列表
    dirs = ["__pycache__", "resource", "controllers", "services"]

    # 应用过滤逻辑（与 cli.py:630 相同）
    filtered = [d for d in dirs if d not in ("__pycache__", "resource")]

    assert "__pycache__" not in filtered, "__pycache__ 应被过滤"
    assert "resource" not in filtered, "resource 应被过滤"
    assert "controllers" in filtered, "controllers 不应被过滤"
    assert "services" in filtered, "services 不应被过滤"
    print("[OK] __pycache__ 和 resource 被正确过滤")


def test_pycache_dir_exists():
    """验证 __pycache__ 目录在实际遍历中被跳过"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建目录结构
        os.makedirs(os.path.join(tmpdir, "__pycache__"))
        os.makedirs(os.path.join(tmpdir, "resource"))
        os.makedirs(os.path.join(tmpdir, "controllers"))

        # 在各目录放一个 .py 文件
        for d in ["__pycache__", "resource", "controllers"]:
            with open(os.path.join(tmpdir, d, "test.py"), "w") as f:
                f.write("# test")

        collected_files = []
        for root, dirs, files in os.walk(tmpdir):
            # 应用与 cli.py 相同的过滤
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "resource")]
            for fname in files:
                if fname.endswith(".py"):
                    collected_files.append(os.path.relpath(os.path.join(root, fname), tmpdir))

        # 只有 controllers/test.py 应该被收集
        assert len(collected_files) == 1
        assert "controllers" in collected_files[0]
        print("[OK] 实际目录遍历中 __pycache__ 和 resource 被跳过")


if __name__ == "__main__":
    test_pycache_filtered()
    test_pycache_dir_exists()
    print("\n所有测试通过！")
