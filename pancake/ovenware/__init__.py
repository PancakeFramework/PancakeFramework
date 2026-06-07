"""
Ovenware 插件模块
提供插件基类 InitAction 和依赖检查工具
"""

import builtins
import logging

logger = logging.getLogger(__name__)


def check_dependencies(deps: list[str], extras: str = None) -> bool:
    """
    统一依赖检查

    Args:
        deps: 需要检查的 Python 包名列表
        extras: pip extras 名称（如 "redis", "ai"）

    Returns:
        True = 全部可用, False = 有缺失
    """
    missing = []
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if not missing:
        return True
    msg = f"缺少可选依赖: {', '.join(missing)}"
    if extras:
        msg += f"，请运行: pip install pancake[{extras}]"
    logger.warning(msg)
    return False


class InitAction:
    """插件基类 — 所有 ovenware 插件的父类

    属性:
        init_order:  加载顺序（值小先加载, embed=-10, mybatis=1, web=50）
        build_order: 构建顺序（值大先执行）
    """

    init_order: int = 50
    build_order: int = 0

    def check(self) -> bool:
        """环境检查，返回 True 表示可以加载"""
        return True

    def build(self):
        """构建阶段，按 build_order 执行"""
        pass

    async def startup(self):
        """启动阶段"""
        pass

    async def shutdown(self):
        """关闭阶段（逆序执行）"""
        pass

    async def loop_method(self):
        """循环方法（如 Web 服务器）"""
        pass

    def get_info(self) -> dict:
        """返回插件元信息"""
        return {
            "name": type(self).__name__,
            "init_order": self.init_order,
            "build_order": self.build_order,
        }


# 注册到 builtins 供插件使用
builtins.__dict__["logging"] = logging
builtins.__dict__["check_dependencies"] = check_dependencies
