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
        # 保存依赖列表供 load_dlc 使用
        settings.set("_xml_dependencies", xml_data.get("dependencies", []))


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
    """构建服务 — 创建所有 Bean 并启动

    使用 get_event_loop().run_until_complete() 避免创建多个事件循环，
    确保 Bean 的 async 资源（如数据库连接）在后续 loop_method 中可用。
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 已有运行中的事件循环（如 Jupyter），创建 task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, builder.build.async_build()).result()
    else:
        # 正常情况：使用现有循环或创建新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(builder.build.async_build())
        finally:
            # 不关闭循环，留给后续 loop_method 使用
            pass


def _get_loop_methods() -> dict:
    """从 DoughFactory 中获取所有注册的 loop_method

    跳过 InitAction 基类的默认空实现。
    """
    from pancake.ovenware import InitAction
    factory = DoughFactory.get()
    loop_methods = {}

    for name, instance in factory.get_all_instances().items():
        if hasattr(instance, 'loop_method') and callable(instance.loop_method):
            # 跳过未覆盖基类默认空实现的插件
            if isinstance(instance, InitAction) and type(instance).loop_method is InitAction.loop_method:
                continue
            loop_methods[name] = instance.loop_method

    return loop_methods


def run_loop_methods():
    """运行所有 loop_method（并发执行，避免互相阻塞）

    通过配置 framework.main_loop 指定主线程运行的 loop_method 名称。
    未配置时默认第一个 loop_method 在主线程运行。
    """
    import threading
    from pancake import settings

    loop_methods = _get_loop_methods()
    if not loop_methods:
        return

    if len(loop_methods) == 1:
        name, method = next(iter(loop_methods.items()))
        logger.info(f"运行 loop_method: {name}")
        method()
        return

    items = list(loop_methods.items())

    # 通过配置指定主线程 loop_method
    main_loop_name = settings.get("framework.main_loop")
    main_idx = 0
    if main_loop_name:
        for i, (name, method) in enumerate(items):
            if name == main_loop_name:
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
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(factory.async_shutdown_all())
            else:
                loop.run_until_complete(factory.async_shutdown_all())
        except RuntimeError:
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
