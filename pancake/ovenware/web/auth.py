"""
认证与授权模块
提供全局认证回调、角色检查、auth_required / role_required 装饰器
"""

import functools
import inspect
import logging
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)

# 认证回调: Callable[[Request, str | None], Any]
_auth_handler: Callable | None = None
# 角色检查回调: Callable[[Request, Any, list[str]], bool]
_role_handler: Callable | None = None


def set_auth_handler(handler: Callable):
    """注册全局认证回调

    handler 签名: async def handler(request: Request, token: str | None) -> Any
    返回值会作为 current_user 传给路由函数和角色检查。
    认证失败应抛出 HTTPException(401)。
    """
    global _auth_handler
    _auth_handler = handler
    logger.info("Web 认证回调已注册")


def set_role_handler(handler: Callable):
    """注册全局角色检查回调

    handler 签名: async def handler(request: Request, user: Any, roles: list[str]) -> bool
    返回 False 表示权限不足，抛出 403。
    """
    global _role_handler
    _role_handler = handler
    logger.info("Web 角色检查回调已注册")


async def _get_current_user(request: Request) -> Any:
    """FastAPI 依赖：解析认证信息并返回用户对象"""
    if _auth_handler is None:
        return None
    credentials: HTTPAuthorizationCredentials | None = await _security(request)
    token = credentials.credentials if credentials else None
    return await _auth_handler(request, token)


def _inject_dependency(func: Callable, param_name: str, annotation: Any, default: Any):
    """向函数签名注入一个 FastAPI Depends 参数"""
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    new_param = inspect.Parameter(
        param_name,
        inspect.Parameter.KEYWORD_ONLY,
        default=default,
        annotation=annotation,
    )
    # 避免重复注入
    if param_name not in sig.parameters:
        params.append(new_param)
    func.__signature__ = sig.replace(parameters=params)


def auth_required(func: Callable) -> Callable:
    """认证装饰器 — 路由必须通过认证

    装饰后，函数签名中可声明 current_user 参数获取用户对象。
    """
    sig = inspect.signature(func)
    has_current_user = "current_user" in sig.parameters

    @functools.wraps(func)
    async def wrapper(*args, request: Request = None, current_user: Any = Depends(_get_current_user), **kwargs):
        if current_user is None and _auth_handler is not None:
            raise HTTPException(status_code=401, detail="未认证")
        if has_current_user:
            kwargs["current_user"] = current_user
        return await func(*args, **kwargs)

    # 保留原始签名但注入 Depends
    _inject_dependency(wrapper, "current_user", Any, Depends(_get_current_user))
    wrapper._auth_required = True
    return wrapper


def role_required(*roles: str):
    """角色授权装饰器 — 路由要求指定角色

    用法:
        @role_required("admin", "editor")
        async def update_post(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        base = auth_required(func) if not getattr(func, "_auth_required", False) else func

        @functools.wraps(base)
        async def wrapper(*args, request: Request = None, current_user: Any = Depends(_get_current_user), **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="未认证")
            if _role_handler is None:
                raise HTTPException(status_code=500, detail="未配置角色检查回调，请调用 set_role_handler()")
            if not await _role_handler(request, current_user, list(roles)):
                raise HTTPException(status_code=403, detail=f"需要角色: {', '.join(roles)}")
            return await base(*args, request=request, **kwargs)

        _inject_dependency(wrapper, "current_user", Any, Depends(_get_current_user))
        wrapper._auth_required = True
        return wrapper
    return decorator
