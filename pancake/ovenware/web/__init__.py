"""
Web 服务插件
提供 Filter Chain、控制器装饰器、认证授权、限流、WebSocket 等功能

所有公开 API 通过此文件 re-export，保持向后兼容：
  from pancake.ovenware.web import get_controller, filter, Filter
"""

from .auth import auth_required, role_required, set_auth_handler, set_role_handler
from .filter import Filter, filter, middleware
from .controller import (
    get_controller, post_controller, put_controller,
    delete_controller, patch_controller, page_controller,
    post_auto_controller, get_auto_controller,
    validate,
)
from .middleware import transaction, rate_limit
from .websocket import websocket_controller
from .metrics import get_metrics
from .main import Main

# 注册到 oven，使 embed 自动注入到 builtins
from pancake import oven

# 控制器装饰器
oven.muffin_flour["get_controller"] = get_controller
oven.muffin_flour["post_controller"] = post_controller
oven.muffin_flour["put_controller"] = put_controller
oven.muffin_flour["delete_controller"] = delete_controller
oven.muffin_flour["patch_controller"] = patch_controller
oven.muffin_flour["page_controller"] = page_controller

# 认证 / 授权
oven.muffin_flour["auth_required"] = auth_required
oven.muffin_flour["role_required"] = role_required
oven.muffin_flour["set_auth_handler"] = set_auth_handler
oven.muffin_flour["set_role_handler"] = set_role_handler

# Filter Chain
oven.muffin_flour["filter"] = filter
oven.muffin_flour["Filter"] = Filter

# 事务
oven.muffin_flour["transaction"] = transaction

# 中间件 / 校验（向后兼容）
oven.muffin_flour["middleware"] = middleware
oven.muffin_flour["validate"] = validate

# 限流
oven.muffin_flour["rate_limit"] = rate_limit

# WebSocket
oven.muffin_flour["websocket_controller"] = websocket_controller
