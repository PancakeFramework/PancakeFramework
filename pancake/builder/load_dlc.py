"""
插件加载模块
从 XML 配置加载插件，通过 import 发现，缺失时自动 pip install
"""

import sys
import importlib
import inspect
import logging
import subprocess

from pancake.registry import register_decorator
from pancake.factory.dough_factory import DoughFactory
from pancake import settings
from pancake.exceptions import PluginError

logger = logging.getLogger(__name__)


def _resolve_package_name(group_id: str, artifact_id: str) -> str:
    """根据 groupId 和 artifactId 推算 Python 包名

    io.pancake → pancake_{artifactId}（连字符转下划线）
    其他       → {groupId}_{artifactId}
    """
    if group_id == "io.pancake":
        return f"pancake_{artifact_id}".replace("-", "_")
    return f"{group_id}_{artifact_id}".replace("-", "_")


def _try_import(package_name: str):
    """尝试 import，失败则 pip install 后重试"""
    try:
        return importlib.import_module(package_name)
    except ImportError:
        pass

    # 自动安装
    logger.info(f"插件 {package_name} 未安装，正在 pip install ...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"pip install {package_name} 失败:\n{result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"pip install {package_name} 超时")

    # 安装后重新 import
    try:
        # 清除缓存确保重新加载
        if package_name in sys.modules:
            del sys.modules[package_name]
        return importlib.import_module(package_name)
    except ImportError as e:
        raise RuntimeError(
            f"pip install {package_name} 成功但仍无法导入: {e}"
        )


def _load_plugins():
    """从 XML dependencies 加载所有插件"""
    dependencies = settings.get("_xml_dependencies", [])
    if not dependencies:
        logger.info("No plugins configured in XML")
        return {}

    disabled = settings.get("framework.disable_dlc", [])
    main_classes = {}

    for dep in dependencies:
        group_id = dep.get("groupId", "io.pancake")
        artifact_id = dep.get("artifactId", "")
        enabled = dep.get("enabled", True)
        if not artifact_id or not enabled:
            continue

        name = artifact_id

        if name in disabled:
            logger.info(f"Plugin {name} disabled, skipping")
            continue

        # 推算包名并导入
        package_name = _resolve_package_name(group_id, artifact_id)

        try:
            plugin = _try_import(package_name)
        except RuntimeError as e:
            raise PluginError(str(e)) from e

        # 扫描模块中的类和函数
        all_items = {}
        for attr_name, member in inspect.getmembers(plugin):
            if (
                (not attr_name.startswith("_"))
                and (inspect.isclass(member) or inspect.isfunction(member))
                and (member.__module__ == plugin.__name__
                     or member.__module__.startswith(plugin.__name__ + "."))
            ):
                all_items[attr_name] = member

        # 注册装饰器到 registry
        for item_name, obj in all_items.items():
            if inspect.isclass(obj) and hasattr(obj, 'build') and hasattr(obj, 'init_order'):
                continue
            register_decorator(item_name, obj)

        # 注册 Main 类（init_order/build_order 从类自身读取）
        for item_name, obj in all_items.items():
            if inspect.isclass(obj) and hasattr(obj, 'build') and hasattr(obj, 'init_order'):
                main_classes[name] = {"class": obj}
                break
        else:
            logger.info(f"Plugin {name} loaded (no Main class)")

    return main_classes


def run():
    """加载插件：从 XML 配置读取，import + 自动 pip install"""
    logger.info("Loading plugins from XML config")
    main_classes = _load_plugins()

    # 按插件自身 init_order 排序，初始化插件
    sorted_plugins = sorted(main_classes.items(), key=lambda x: x[1]["class"].init_order)

    for plugin_name, plugin_info in sorted_plugins:
        cls = plugin_info["class"]

        try:
            instance = cls()
        except Exception as e:
            raise PluginError(f"插件 {plugin_name} 初始化失败: {e}") from e

        # 检查 check 方法
        if hasattr(instance, 'check'):
            try:
                if not instance.check():
                    logger.info(f"Plugin {plugin_name} check failed, skipping")
                    continue
            except Exception as e:
                raise PluginError(f"插件 {plugin_name} 检查失败: {e}") from e

        # 注册到 DoughFactory
        factory = DoughFactory.get()
        factory.register_instance(plugin_name, instance)

        logger.info(f"Plugin {plugin_name} loaded (init_order={cls.init_order})")
