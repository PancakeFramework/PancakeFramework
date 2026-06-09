"""项目命令：init, create, check, run, build"""

import os
import subprocess
import sys


def cmd_init(args):
    """在当前目录初始化项目"""
    cwd = os.getcwd()

    if os.path.exists("main.py"):
        print("错误: 当前目录已有 main.py，看起来已经是一个项目")
        sys.exit(1)

    name = os.path.basename(cwd)
    print(f"在当前目录初始化项目: {name}")

    dirs = [
        os.path.join("src", "resource", "yaml"),
        os.path.join("src", "resource", "json"),
        os.path.join("src", "mapper"),
        os.path.join("src", "templates"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    with open("main.py", "w", encoding="utf-8") as f:
        f.write('import pancake\n\npancake.run()\n')

    with open("pancake.xml", "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<pancake>
    <config>
        <pancake.title>{name}</pancake.title>
    </config>
    <dependencies>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>embed</artifactId>
        </dependency>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>mybatis</artifactId>
        </dependency>
    </dependencies>
</pancake>
''')

    with open(os.path.join("src", "resource", "yaml", "service.yaml"), "w", encoding="utf-8") as f:
        f.write(f'''# 自定义配置（覆盖 pancake.xml 中的值）
# pancake:
#   title: {name}
''')

    print("项目初始化完成!")
    print("  python main.py")


def cmd_create(args):
    """创建新项目"""
    name = args.name
    project_dir = os.path.join(os.getcwd(), name)

    if os.path.exists(project_dir):
        print(f"错误: 目录 '{name}' 已存在")
        sys.exit(1)

    print(f"创建项目: {name}")

    dirs = [
        os.path.join(project_dir, "src", "resource", "yaml"),
        os.path.join(project_dir, "src", "resource", "json"),
        os.path.join(project_dir, "src", "mapper"),
        os.path.join(project_dir, "src", "templates"),
    ]
    for d in dirs:
        os.makedirs(d)

    with open(os.path.join(project_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write('import pancake\n\npancake.run()\n')

    with open(os.path.join(project_dir, "pancake.xml"), "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<pancake>
    <config>
        <pancake.title>{name}</pancake.title>
    </config>
    <dependencies>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>embed</artifactId>
        </dependency>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>mybatis</artifactId>
        </dependency>
    </dependencies>
</pancake>
''')

    with open(os.path.join(project_dir, "src", "resource", "yaml", "service.yaml"), "w", encoding="utf-8") as f:
        f.write(f'''pancake:
  title: {name}
''')

    with open(os.path.join(project_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(f'''[tool.poetry]
name = "{name}"
version = "0.1.0"
description = "A Pancake framework project"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
pancake = "*"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
''')

    print(f"项目 '{name}' 创建成功!")
    print(f"  cd {name}")
    print(f"  pip install pancake")
    print(f"  python main.py")


def cmd_check(args):
    """检查项目结构和环境"""
    print("检查项目结构...")

    errors = []
    warnings = []

    if not os.path.exists("main.py"):
        errors.append("缺少 main.py")
    else:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "import pancake" not in content:
                warnings.append("main.py 中未找到 'import pancake'")

    if not os.path.exists("pancake.xml"):
        warnings.append("缺少 pancake.xml（可选，用于插件配置）")

    if not os.path.isdir("src"):
        errors.append("缺少 src 目录")
    else:
        yaml_dir = os.path.join("src", "resource", "yaml")
        if not os.path.isdir(yaml_dir):
            warnings.append(f"缺少 {yaml_dir} 目录")
        else:
            yaml_files = [f for f in os.listdir(yaml_dir) if f.endswith(('.yaml', '.yml'))]
            if not yaml_files:
                warnings.append(f"{yaml_dir} 中没有 YAML 配置文件")

        template_dir = os.path.join("src", "templates")
        if not os.path.isdir(template_dir):
            warnings.append(f"缺少 {template_dir} 目录（模板渲染需要）")

    try:
        import pancake  # noqa: F401
        print("  [OK] pancake 已安装")
    except ImportError:
        errors.append("pancake 未安装，请运行: pip install pancake")

    if errors:
        print("\n错误:")
        for e in errors:
            print(f"  [ERROR] {e}")

    if warnings:
        print("\n警告:")
        for w in warnings:
            print(f"  [WARN] {w}")

    if not errors and not warnings:
        print("  项目结构正常!")

    return len(errors) == 0


def cmd_run(args):
    """运行项目"""
    if not os.path.exists("main.py"):
        print("错误: 当前目录没有 main.py，请在项目根目录运行")
        sys.exit(1)

    print("启动 Pancake 项目...")
    import pancake
    pancake.run()


def cmd_build(args):
    """打包项目为 wheel"""
    if not os.path.exists("pyproject.toml"):
        print("错误: 当前目录没有 pyproject.toml")
        sys.exit(1)

    print("打包项目...")
    result = subprocess.run(
        [sys.executable, "-m", "poetry", "build"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("打包成功!")
        print(result.stdout)
    else:
        print("打包失败:")
        print(result.stderr)
        sys.exit(1)
