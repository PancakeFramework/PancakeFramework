"""
Pancake 启动流水线
load_config -> load_ovenware -> load_dish -> build -> run_loop
"""

import logging
import signal
import sys

from pancake import settings
from .tool import ProgressBar
from . import builder
from pancake.factory.dough_factory import DoughFactory

logger = logging.getLogger("Pancake_Main")


def load_xml():
    """加载 XML 启动配置，合并到 settings"""
    from pancake.resource import xml_config
    xml_data = xml_config.load_xml()
    if xml_data:
        # 合并全局配置
        global_config = xml_data.get("config", {})
        if global_config:
            settings.init(global_config)
        # 插件配置也合并到 settings
        for plugin in xml_data.get("plugins", []):
            plugin_config = plugin.get("config", {})
            if plugin_config:
                settings.init(plugin_config)
        # 保存 XML 原始数据供 load_dlc 使用
        settings.set("_xml_plugins", xml_data.get("plugins", []))


def load_config():
    """加载 YAML/JSON 配置文件，合并到 settings"""
    from pancake.resource import json, yml

    yaml_data = yml.yaml_init()
    json_data = json.json_init()

    if yaml_data:
        settings.init(yaml_data)
    if json_data:
        settings.init(json_data)

    # 确保 disable_dlc 存在
    if "framework.disable_dlc" not in settings.get_all():
        settings.set("framework.disable_dlc", [])


def load_ovenware():
    """加载插件"""
    builder.load_dlc.run()


def load_dish():
    """加载用户代码"""
    builder.load_src.run()


def build_all():
    """构建服务 — 创建所有 Bean 并启动"""
    import asyncio
    asyncio.run(builder.build.async_build())


def _get_loop_methods() -> dict:
    """从 DoughFactory 中获取所有注册的 loop_method"""
    factory = DoughFactory.get()
    loop_methods = {}

    # 从已注册的实例中查找 loop_method
    for name, instance in factory.get_all_instances().items():
        if hasattr(instance, 'loop_method') and callable(instance.loop_method):
            loop_methods[name] = instance.loop_method

    return loop_methods


def run_loop_methods():
    """运行所有 loop_method（并发执行，避免互相阻塞）

    web 服务器始终在主线程运行（保持进程存活），
    其余 loop_method 在守护线程中运行。
    """
    import threading

    loop_methods = _get_loop_methods()
    if not loop_methods:
        return

    if len(loop_methods) == 1:
        name, method = next(iter(loop_methods.items()))
        logger.info(f"运行 loop_method: {name}")
        method()
        return

    # 多个 loop_method：web 在主线程，其余在守护线程
    items = list(loop_methods.items())

    # 找到 web 相关的 loop_method 放主线程
    main_idx = 0
    for i, (name, method) in enumerate(items):
        if "web" in name.lower():
            main_idx = i
            break

    for i, (name, method) in enumerate(items):
        if i == main_idx:
            continue
        logger.info(f"运行 loop_method (后台): {name}")
        t = threading.Thread(target=method, daemon=True, name=f"loop_{name}")
        t.start()

    main_name, main_method = items[main_idx]
    logger.info(f"运行 loop_method (主线程): {main_name}")
    main_method()


def _shutdown_handler(signum, frame):
    """信号处理：优雅关闭"""
    import asyncio
    sig_name = signal.Signals(signum).name
    logger.info(f"收到信号 {sig_name}，正在优雅关闭...")

    factory = DoughFactory.get()
    try:
        asyncio.run(factory.async_shutdown_all())
    except Exception as e:
        logger.error(f"关闭失败: {e}")

    logger.info("Pancake 已关闭")
    sys.exit(0)


def run():
    """运行服务"""
    # 注册信号处理
    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    loading_list = {
        "load xml": load_xml,
        "load config": load_config,
        "load ovenware": load_ovenware,
        "load dish": load_dish,
        "build": build_all,
    }

    logger.info("Pancake Loading...")

    progress_bar = ProgressBar(len(loading_list), "Pancake Loading")

    for task in loading_list.keys():
        loading_list[task]()
        progress_bar.update(1, f"{task} 完成")
    progress_bar.finish()
    logger.info("Pancake Loading 完成")

    logger.info("Pancake 启动完成")

    # 运行 loop_method（如 web 服务器）
    run_loop_methods()
