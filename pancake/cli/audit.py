"""代码审核命令：audit"""

import ast
import os
import sys

from pancake.exceptions import ProjectError


def cmd_audit(args):
    """审核 src/ 代码质量"""
    src_dir = "src"
    if not os.path.isdir(src_dir):
        raise ProjectError(f"{src_dir} 目录不存在")

    issues = []
    file_count = 0

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "resource")]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            file_count += 1

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=fpath)
            except SyntaxError as e:
                issues.append((fpath, f"语法错误: {e}"))
                continue

            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if isinstance(node, ast.Assign):
                    continue
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    continue
                # 跳过 if __name__ == "__main__": 块
                if isinstance(node, ast.If):
                    if (isinstance(node.test, ast.Compare)
                            and isinstance(node.test.left, ast.Name)
                            and node.test.left.id == "__name__"):
                        continue

                node_type = type(node).__name__
                lineno = getattr(node, "lineno", "?")
                issues.append((fpath, f"第 {lineno} 行: 非声明语句 ({node_type})"))

    print(f"扫描 {file_count} 个文件")
    if issues:
        print(f"\n发现 {len(issues)} 个问题:")
        for fpath, msg in issues:
            print(f"  [WARN] {fpath}: {msg}")
    else:
        print("  代码结构良好，未发现问题")
