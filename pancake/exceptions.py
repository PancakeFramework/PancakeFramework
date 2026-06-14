"""Pancake 框架异常"""


class PancakeError(Exception):
    """框架基础异常"""
    pass


class ConfigError(PancakeError):
    """配置相关错误"""
    pass


class PluginError(PancakeError):
    """插件加载错误"""
    pass


class BuildError(PancakeError):
    """Bean 构建错误"""
    pass


class DependencyError(PancakeError):
    """依赖检查/安装错误"""
    pass


class ProjectError(PancakeError):
    """项目结构错误"""
    pass
