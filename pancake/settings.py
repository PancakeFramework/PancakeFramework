"""
Pancake 配置管理模块
统一管理所有配置项：路径、服务、数据库等

配置优先级：XML > YAML > 默认值

用户可通过 pancake.xml 的 <global> 节点或 YAML 配置覆盖默认值
"""

import os

# 默认配置
_DEFAULTS = {
    # 路径配置
    "paths.src_dir": "src",
    "paths.yaml_dir": os.path.join("src", "resource", "yaml"),
    "paths.json_dir": os.path.join("src", "resource", "json"),
    "paths.mapper_dir": os.path.join("src", "mapper"),
    "paths.controller_dir": os.path.join("src", "controller"),
    "paths.db_dir": os.path.join("src", "resource", "db"),
    "paths.template_dir": os.path.join("src", "templates"),
    "paths.static_dir": os.path.join("src", "static"),

    # 服务配置
    "service.title": "Pancake App",
    "service.version": "1.0.0",
    "service.host": "127.0.0.1",
    "service.port": 8080,

    # 数据库配置
    "mybatis.database.url": None,  # 由 mybatis config 提供默认值
}

# 用户配置（从 XML/YAML 加载）
_user_config: dict = {}

# 项目根目录
_project_root: str = None


def init(config: dict = None):
    """
    初始化配置（在 run() 流程中调用）
    将 XML/YAML 配置合并到用户配置中
    """
    global _user_config
    if config:
        _user_config.update(config)


def set_project_root(path: str):
    """设置项目根目录"""
    global _project_root
    _project_root = path


def get_project_root() -> str:
    """获取项目根目录（未显式设置时使用 cwd）"""
    if _project_root is not None:
        return _project_root
    return os.getcwd()


def get(key: str, default=None):
    """
    获取配置值
    优先级：用户配置 > 传入默认值 > 内置默认值
    """
    if key in _user_config:
        return _user_config[key]
    if default is not None:
        return default
    return _DEFAULTS.get(key)


def get_path(name: str) -> str:
    """
    获取路径配置（返回绝对路径）
    name 如 "yaml_dir", "mapper_dir" 等
    """
    key = f"paths.{name}"
    rel = get(key)
    if rel is None:
        return None
    if os.path.isabs(rel):
        return rel
    return os.path.join(get_project_root(), rel)


def get_all(prefix: str = None) -> dict:
    """获取所有配置，可选按前缀过滤"""
    result = dict(_DEFAULTS)
    result.update(_user_config)
    if prefix:
        result = {k: v for k, v in result.items() if k.startswith(prefix)}
    return result


def set(key: str, value):
    """手动设置配置值"""
    _user_config[key] = value


def reset():
    """重置所有配置（用于测试）"""
    global _user_config, _project_root
    _user_config = {}
    _project_root = None
