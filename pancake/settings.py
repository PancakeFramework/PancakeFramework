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
    "paths.db_dir": os.path.join("src", "resource", "db"),
    "paths.template_dir": os.path.join("src", "templates"),
    "paths.static_dir": os.path.join("src", "static"),

    # 服务配置
    "service.title": "Pancake App",
    "service.version": "1.0.0",
    "service.host": "127.0.0.1",
    "service.port": 8080,
    "service.description": "",
    "service.docs_enabled": True,
    "service.metrics_enabled": True,
    "service.timeout": 30,

    # 数据库配置
    "mybatis.database.url": None,  # 由 mybatis config 提供默认值

    # 外部服务地址
    "redis.url": "redis://localhost:6379",
    "redis.db": 0,
    "mongo.url": "mongodb://localhost:27017",
    "mongo.db": "pancake",
    "grpc.url": "localhost:50051",
    "ollama.url": "http://localhost:11434",

    # AI 配置
    "ai.timeout": 60,
    "ai.retry": 3,

    # Web 配置（pancake-web 插件）
    "web.host": "127.0.0.1",
    "web.port": 8080,
    "web.debug": False,
    "web.static": os.path.join("src", "static"),
    "web.templates": os.path.join("src", "templates"),
    "web.cors.allow_origins": "*",
    "web.cors.allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
    "web.cors.allow_headers": "*",
    "web.cors.max_age": 3600,
    "web.session.secret_key": None,
    "web.session.max_age": 86400,
    "web.session.secure": False,
    "web.request.timeout": 30,
    "web.request.max_body_size": 1048576,
    "web.server.max_connections": 100,
    "web.server.backlog": 128,
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


def replace(config: dict = None):
    """
    替换配置（用于热重载）
    清空旧的用户配置，应用新的配置。
    确保被删除的 key 不会残留。
    """
    global _user_config
    _user_config = dict(config) if config else {}


def set_project_root(path: str):
    """设置项目根目录"""
    global _project_root
    _project_root = path


def get_project_root() -> str:
    """获取项目根目录（未显式设置时使用 cwd）"""
    if _project_root is not None:
        return _project_root
    return os.getcwd()


_UNSET = object()


def get(key: str, default=_UNSET):
    """
    获取配置值
    优先级：用户配置 > 内置默认值 > 传入默认值

    如果 key 存在于用户配置或内置默认值中，返回对应值。
    否则返回传入的 default（如果提供），或 None。
    """
    if key in _user_config:
        return _user_config[key]
    if key in _DEFAULTS:
        return _DEFAULTS[key]
    if default is not _UNSET:
        return default
    return None


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
