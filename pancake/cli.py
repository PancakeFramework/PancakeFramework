"""
Pancake CLI - 命令行工具
支持 version / init / create / run / check / build / plugin / config / audit / update / install
"""

import argparse
import ast
import os
import subprocess
import sys
import xml.etree.ElementTree as ET


def _get_version():
    """获取框架版本"""
    try:
        from importlib.metadata import version
        return version("pancake_framework")
    except Exception:
        pass
    # 回退：从 pyproject.toml 读取
    try:
        import tomllib
        pyproject = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
        with open(pyproject, "rb") as f:
            return tomllib.load(f)["tool"]["poetry"]["version"]
    except Exception:
        pass
    # 回退：从 __init__.py 读取
    return "unknown"


# ============================================================
#  version
# ============================================================

def cmd_version(args):
    """显示框架版本"""
    print(f"Pancake Framework v{_get_version()}")


# ============================================================
#  cover — 显示封面
# ============================================================

def cmd_cover(args):
    """显示 Pancake 封面"""
    from pancake.initialize.print_ico import print_cover
    print_cover()


# ============================================================
#  init — 在当前目录初始化项目
# ============================================================

def cmd_init(args):
    """在当前目录初始化项目"""
    cwd = os.getcwd()

    # 检查是否已有项目文件
    if os.path.exists("main.py"):
        print("错误: 当前目录已有 main.py，看起来已经是一个项目")
        sys.exit(1)

    name = os.path.basename(cwd)
    print(f"在当前目录初始化项目: {name}")

    # 创建目录结构
    dirs = [
        os.path.join("src", "resource", "yaml"),
        os.path.join("src", "resource", "json"),
        os.path.join("src", "mapper"),
        os.path.join("src", "controller"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # 创建 main.py
    with open("main.py", "w", encoding="utf-8") as f:
        f.write('import pancake\n\npancake.run()\n')

    # 创建 pancake.xml
    with open("pancake.xml", "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<pancake>
    <groupId>com.example</groupId>
    <artifactId>{name}</artifactId>
    <version>1.0.0</version>

    <global>
        <service.title>{name}</service.title>
        <service.version>1.0.0</service.version>
        <service.host>127.0.0.1</service.host>
        <service.port>8080</service.port>
    </global>

    <dependencies>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>embed</artifactId>
        </dependency>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>mybatis</artifactId>
        </dependency>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>web</artifactId>
        </dependency>
    </dependencies>
</pancake>
''')

    # 创建 service.yaml
    with open(os.path.join("src", "resource", "yaml", "service.yaml"), "w", encoding="utf-8") as f:
        f.write(f'''service:
  title: {name}
  version: 1.0.0
  host: 127.0.0.1
  port: 8080
''')

    print("项目初始化完成!")
    print("  python main.py")


# ============================================================
#  create — 在子目录创建项目
# ============================================================

def cmd_create(args):
    """创建新项目"""
    name = args.name
    project_dir = os.path.join(os.getcwd(), name)

    if os.path.exists(project_dir):
        print(f"错误: 目录 '{name}' 已存在")
        sys.exit(1)

    print(f"创建项目: {name}")

    # 创建目录结构
    dirs = [
        os.path.join(project_dir, "src", "resource", "yaml"),
        os.path.join(project_dir, "src", "resource", "json"),
        os.path.join(project_dir, "src", "mapper"),
        os.path.join(project_dir, "src", "controller"),
    ]
    for d in dirs:
        os.makedirs(d)

    # 创建 main.py
    with open(os.path.join(project_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write('import pancake\n\npancake.run()\n')

    # 创建 pancake.xml
    with open(os.path.join(project_dir, "pancake.xml"), "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<pancake>
    <groupId>com.example</groupId>
    <artifactId>{name}</artifactId>
    <version>1.0.0</version>

    <global>
        <service.title>{name}</service.title>
        <service.version>1.0.0</service.version>
        <service.host>127.0.0.1</service.host>
        <service.port>8080</service.port>
    </global>

    <dependencies>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>embed</artifactId>
        </dependency>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>mybatis</artifactId>
        </dependency>
        <dependency>
            <groupId>io.pancake</groupId>
            <artifactId>web</artifactId>
        </dependency>
    </dependencies>
</pancake>
''')

    # 创建 service.yaml
    with open(os.path.join(project_dir, "src", "resource", "yaml", "service.yaml"), "w", encoding="utf-8") as f:
        f.write(f'''service:
  title: {name}
  version: 1.0.0
  host: 127.0.0.1
  port: 8080
''')

    # 创建 pyproject.toml
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


# ============================================================
#  check — 检查项目结构
# ============================================================

def cmd_check(args):
    """检查项目结构和环境"""
    print("检查项目结构...")

    errors = []
    warnings = []

    # 检查 main.py
    if not os.path.exists("main.py"):
        errors.append("缺少 main.py")
    else:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "import pancake" not in content:
                warnings.append("main.py 中未找到 'import pancake'")

    # 检查 pancake.xml
    if not os.path.exists("pancake.xml"):
        warnings.append("缺少 pancake.xml（可选，用于插件配置）")

    # 检查 src 目录
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

    # 检查 pancake 是否安装
    try:
        import pancake  # noqa: F401
        print("  [OK] pancake 已安装")
    except ImportError:
        errors.append("pancake 未安装，请运行: pip install pancake")

    # 输出结果
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


# ============================================================
#  run — 运行项目
# ============================================================

def cmd_run(args):
    """运行项目"""
    if not os.path.exists("main.py"):
        print("错误: 当前目录没有 main.py，请在项目根目录运行")
        sys.exit(1)

    print("启动 Pancake 项目...")
    import pancake
    pancake.run()


# ============================================================
#  build — 打包项目
# ============================================================

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


# ============================================================
#  plugin — 插件管理
# ============================================================

def _find_ovenware_dir():
    """找到 ovenware 目录"""
    dlc_dir = os.path.join(os.path.dirname(__file__), "ovenware")
    if os.path.isdir(dlc_dir):
        return dlc_dir
    return None


def _get_disabled_plugins():
    """从 pancake.xml 获取禁用的插件列表"""
    disabled = set()
    xml_path = os.path.join(os.getcwd(), "pancake.xml")
    if not os.path.exists(xml_path):
        return disabled
    try:
        tree = ET.parse(xml_path)
        for plugin in tree.getroot().findall(".//plugin"):
            name = plugin.get("name")
            enabled = plugin.get("enabled", "true").lower()
            if name and enabled == "false":
                disabled.add(name)
    except Exception:
        pass
    return disabled


def cmd_plugin_list(args):
    """列出可用插件"""
    ovenware_dir = _find_ovenware_dir()
    if not ovenware_dir:
        print("错误: 找不到 ovenware 目录")
        sys.exit(1)

    disabled = _get_disabled_plugins()

    # 扫描插件
    entries = os.listdir(ovenware_dir)
    plugins = []

    for entry in sorted(entries):
        full = os.path.join(ovenware_dir, entry)
        is_package = os.path.isdir(full) and os.path.exists(os.path.join(full, "__init__.py"))
        is_module = entry.endswith(".py") and entry != "__init__.py"

        if not is_package and not is_module:
            continue

        name = entry.replace(".py", "")
        if name.startswith("_"):
            continue

        # 读取 init_order
        init_order = "-"
        try:
            if is_package:
                mod_path = os.path.join(full, "__init__.py")
            else:
                mod_path = full
            with open(mod_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "init_order":
                                    if isinstance(item.value, ast.Constant):
                                        init_order = str(item.value.value)
        except Exception:
            pass

        enabled = name not in disabled
        status = "enabled" if enabled else "disabled"
        plugins.append((name, init_order, status))

    if not plugins:
        print("未找到插件")
        return

    # 格式化输出
    print(f"{'插件名':<25} {'init_order':<12} {'状态':<10}")
    print("-" * 50)
    for name, order, status in plugins:
        print(f"{name:<25} {order:<12} {status:<10}")


def cmd_plugin_add(args):
    """添加插件到 pancake.xml"""
    name = args.name
    xml_path = os.path.join(os.getcwd(), "pancake.xml")

    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"错误: XML 解析失败: {e}")
        sys.exit(1)

    # 查找 <plugins> 节点
    plugins_elem = root.find("plugins")
    if plugins_elem is None:
        plugins_elem = ET.SubElement(root, "plugins")

    # 检查是否已存在
    for plugin in plugins_elem.findall("plugin"):
        if plugin.get("name") == name:
            print(f"插件 '{name}' 已存在于 pancake.xml")
            return

    # 添加插件
    ET.SubElement(plugins_elem, "plugin", name=name)

    # 写回文件
    ET.indent(tree, space="    ")
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
    print(f"已添加插件 '{name}' 到 pancake.xml")


def cmd_plugin_remove(args):
    """从 pancake.xml 移除指定插件"""
    name = args.name
    xml_path = os.path.join(os.getcwd(), "pancake.xml")

    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"错误: XML 解析失败: {e}")
        sys.exit(1)

    found = False

    # 从 <plugins> 节点移除
    plugins_elem = root.find("plugins")
    if plugins_elem is not None:
        for plugin in plugins_elem.findall("plugin"):
            if plugin.get("name") == name:
                plugins_elem.remove(plugin)
                found = True
                break
        if len(plugins_elem) == 0:
            root.remove(plugins_elem)

    # 从 <dependencies> 节点移除
    deps_elem = root.find("dependencies")
    if deps_elem is not None:
        for dep in deps_elem.findall("dependency"):
            artifact = dep.find("artifactId")
            if artifact is not None and artifact.text == name:
                deps_elem.remove(dep)
                found = True
                break
        if len(deps_elem) == 0:
            root.remove(deps_elem)

    if not found:
        print(f"插件 '{name}' 不存在于 pancake.xml")
        return

    ET.indent(tree, space="    ")
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
    print(f"已从 pancake.xml 移除插件 '{name}'")


def cmd_plugin_clear(args):
    """清空 pancake.xml 中的所有插件"""
    xml_path = os.path.join(os.getcwd(), "pancake.xml")

    if not os.path.exists(xml_path):
        print("错误: 当前目录没有 pancake.xml")
        sys.exit(1)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"错误: XML 解析失败: {e}")
        sys.exit(1)

    count = 0

    # 清空 <plugins> 节点
    plugins_elem = root.find("plugins")
    if plugins_elem is not None:
        count += len(plugins_elem.findall("plugin"))
        root.remove(plugins_elem)

    # 清空 <dependencies> 中的插件
    deps_elem = root.find("dependencies")
    if deps_elem is not None:
        dep_count = len(deps_elem.findall("dependency"))
        count += dep_count
        root.remove(deps_elem)

    if count == 0:
        print("pancake.xml 中没有插件")
        return

    ET.indent(tree, space="    ")
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
    print(f"已清空所有插件 ({count} 个)")


# ============================================================
#  config — 配置管理
# ============================================================

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "credential"}


def _mask_value(key: str, value) -> str:
    """对敏感配置值脱敏"""
    key_lower = key.lower()
    if any(s in key_lower for s in _SENSITIVE_KEYS):
        if isinstance(value, str) and len(value) > 4:
            return value[:2] + "***" + value[-2:]
        return "***"
    return str(value)


def cmd_config_show(args):
    """显示当前配置"""
    # 扫描 YAML 文件
    yaml_dir = os.path.join("src", "resource", "yaml")
    if not os.path.isdir(yaml_dir):
        print(f"警告: {yaml_dir} 目录不存在")
        yaml_dir = None

    configs = {}

    if yaml_dir:
        try:
            import yaml
            for fname in sorted(os.listdir(yaml_dir)):
                if not fname.endswith(('.yaml', '.yml')):
                    continue
                fpath = os.path.join(yaml_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    # 扁平化
                    _flatten_dict(data, f"{fname}:", configs)
        except ImportError:
            print("警告: pyyaml 未安装，无法读取 YAML 配置")
        except Exception as e:
            print(f"警告: 读取配置失败: {e}")

    # 扫描 XML 全局配置
    xml_path = "pancake.xml"
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            global_elem = tree.getroot().find("global") or tree.getroot().find("config")
            if global_elem is not None:
                for child in global_elem:
                    if child.tag != "property" and child.text and child.text.strip():
                        configs[f"xml:{child.tag}"] = child.text.strip()
        except Exception:
            pass

    if not configs:
        print("未找到配置")
        return

    # 输出
    print(f"{'配置项':<40} {'值'}")
    print("-" * 70)
    for key, value in sorted(configs.items()):
        masked = _mask_value(key, value)
        print(f"{key:<40} {masked}")


def _flatten_dict(d: dict, prefix: str, result: dict):
    """扁平化字典"""
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            _flatten_dict(v, f"{key}.", result)
        else:
            result[key] = v


# ============================================================
#  audit — 审核代码
# ============================================================

def cmd_audit(args):
    """审核 src/ 代码质量"""
    src_dir = "src"
    if not os.path.isdir(src_dir):
        print(f"错误: {src_dir} 目录不存在")
        sys.exit(1)

    issues = []
    file_count = 0

    for root, dirs, files in os.walk(src_dir):
        # 跳过 __pycache__ 和 resource
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

            # 检查顶层语句
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if isinstance(node, ast.Assign):
                    # 允许装饰器赋值、类型别名等
                    continue
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    # 允许模块级字符串（docstring）
                    continue

                # 其他语句告警
                node_type = type(node).__name__
                lineno = getattr(node, "lineno", "?")
                issues.append((fpath, f"第 {lineno} 行: 非声明语句 ({node_type})"))

    # 输出结果
    print(f"扫描 {file_count} 个文件")
    if issues:
        print(f"\n发现 {len(issues)} 个问题:")
        for fpath, msg in issues:
            print(f"  [WARN] {fpath}: {msg}")
    else:
        print("  代码结构良好，未发现问题")


# ============================================================
#  update — 更新框架
# ============================================================

def cmd_update(args):
    """更新 pancake_framework 包"""
    print("正在更新 Pancake Framework...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pancake_framework"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("更新成功!")
        # 显示新版本
        new_ver = _get_version()
        print(f"当前版本: v{new_ver}")
        if result.stdout:
            print(result.stdout)
    else:
        print("更新失败:")
        print(result.stderr)
        sys.exit(1)


# ============================================================
#  install — 安装依赖
# ============================================================

def cmd_install(args):
    """安装缺失依赖"""
    print("检查依赖...")

    # 核心依赖
    core_deps = [
        "fastapi", "uvicorn", "pyyaml", "python-dotenv",
        "databases", "aiosqlite",
    ]

    missing = []
    for dep in core_deps:
        module = dep.replace("-", "_").replace("python_", "")
        try:
            __import__(module)
        except ImportError:
            missing.append(dep)

    if not missing:
        print("  核心依赖已全部安装")
        return

    print(f"  缺失: {', '.join(missing)}")
    print("正在安装...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install"] + missing,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("安装成功!")
    else:
        print("安装失败:")
        print(result.stderr)
        sys.exit(1)


# ============================================================
#  主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="pancake",
        description="Pancake Framework - 命令行工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # version
    subparsers.add_parser("version", help="显示框架版本")

    # cover
    subparsers.add_parser("cover", help="显示 Pancake 封面")

    # init
    subparsers.add_parser("init", help="在当前目录初始化项目")

    # create
    create_parser = subparsers.add_parser("create", help="创建新项目")
    create_parser.add_argument("name", help="项目名称")

    # check
    subparsers.add_parser("check", help="检查项目结构和环境")

    # run
    subparsers.add_parser("run", help="运行项目")

    # build
    subparsers.add_parser("build", help="打包项目为 wheel")

    # plugin
    plugin_parser = subparsers.add_parser("plugin", help="插件管理")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_cmd")
    plugin_sub.add_parser("list", help="列出可用插件")
    plugin_add = plugin_sub.add_parser("add", help="添加插件到 pancake.xml")
    plugin_add.add_argument("name", help="插件名称")
    plugin_remove = plugin_sub.add_parser("remove", help="从 pancake.xml 移除插件")
    plugin_remove.add_argument("name", help="插件名称")
    plugin_sub.add_parser("clear", help="清空 pancake.xml 中的所有插件")

    # config
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_sub = config_parser.add_subparsers(dest="config_cmd")
    config_sub.add_parser("show", help="显示当前配置")

    # audit
    subparsers.add_parser("audit", help="审核 src/ 代码质量")

    # update
    subparsers.add_parser("update", help="更新 Pancake Framework")

    # install
    subparsers.add_parser("install", help="安装缺失依赖")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "version": cmd_version,
        "cover": cmd_cover,
        "init": cmd_init,
        "create": cmd_create,
        "check": cmd_check,
        "run": cmd_run,
        "build": cmd_build,
        "audit": cmd_audit,
        "update": cmd_update,
        "install": cmd_install,
    }

    # 处理子命令组
    if args.command == "plugin":
        if args.plugin_cmd == "list":
            cmd_plugin_list(args)
        elif args.plugin_cmd == "add":
            cmd_plugin_add(args)
        elif args.plugin_cmd == "remove":
            cmd_plugin_remove(args)
        elif args.plugin_cmd == "clear":
            cmd_plugin_clear(args)
        else:
            plugin_parser.print_help()
    elif args.command == "config":
        if args.config_cmd == "show":
            cmd_config_show(args)
        else:
            config_parser.print_help()
    elif args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
