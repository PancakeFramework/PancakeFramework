import os
import logging

logger = logging.getLogger(__name__)


def _get_external_plugin_dirs() -> list[str]:
    """
    获取外部插件目录列表

    从环境变量 EXTERNAL_PLUGIN_DIRS 读取
    多个路径用分号(Windows)或冒号(Linux)分隔

    Returns:
        外部插件目录的绝对路径列表
    """
    dirs = []
    env_value = os.getenv("EXTERNAL_PLUGIN_DIRS", "").strip()

    if not env_value:
        return dirs

    # 自动检测分隔符
    separator = ";" if ";" in env_value else ":"

    for path in env_value.split(separator):
        path = path.strip()
        if path:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                dirs.append(abs_path)
            else:
                logger.warning(f"外部插件目录不存在: {abs_path}")

    return dirs

class Main(InitAction):

    def __init__(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "load_src",
            os.path.join(os.path.dirname(__file__), "..", "builder", "load_src.py")
        )
        load_src = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(load_src)

        self.external_plugin_dirs = _get_external_plugin_dirs()
        total_count = 0

        for plugin_dir in self.external_plugin_dirs:
            py_files = load_src.scan_py_files(plugin_dir)
            for filepath in py_files:
                items = load_src.parse_file(filepath)
                if items:
                    load_src.safe_register(filepath)
                    total_count += len(items)

        logger.info(f"成功加载 {total_count} 个外部插件")

    def build(self):
        pass
