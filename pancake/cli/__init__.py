"""
Pancake CLI - 命令行工具
支持 version / init / create / run / check / build / plugin / config / audit / update / install
"""

import argparse
import sys


def main():
    from pancake.exceptions import PancakeError

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

    from .misc import cmd_version, cmd_cover, cmd_update, cmd_install
    from .project import cmd_init, cmd_create, cmd_check, cmd_run, cmd_build
    from .plugin import cmd_plugin_list, cmd_plugin_add, cmd_plugin_remove, cmd_plugin_clear
    from .config import cmd_config_show
    from .audit import cmd_audit

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

    try:
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
    except PancakeError as e:
        # 框架异常：简化输出，完整信息写入 crash/
        from pancake.crash import handle_exception
        simplified, crash_file = handle_exception(e)
        print(f"错误: {simplified}")
        print(f"详细信息已写入: {crash_file}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(0)
    except Exception as e:
        # 未预期异常：同样写入 crash/
        from pancake.crash import handle_exception
        simplified, crash_file = handle_exception(e)
        print(f"未知错误: {simplified}")
        print(f"详细信息已写入: {crash_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
