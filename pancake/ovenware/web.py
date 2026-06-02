"""
Web 服务插件
提供 Web 服务的构建和运行功能，支持完整 HTTP 方法、认证授权、事务
"""

import functools
import inspect
import logging
from typing import Any, Callable

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

from pancake import oven

logger = logging.getLogger(__name__)

# HTTP 方法注册表 key 映射
_METHOD_REGISTRY_KEYS = {
    "GET": "GetController",
    "POST": "PostController",
    "PUT": "PutController",
    "DELETE": "DeleteController",
    "PATCH": "PatchController",
}


# ============================================================
#  认证 / 授权
# ============================================================

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


def auth_required(func: Callable) -> Callable:
    """认证装饰器 — 路由必须通过认证

    装饰后，函数签名中可声明 current_user 参数获取用户对象。
    """
    sig = inspect.signature(func)
    has_current_user = "current_user" in sig.parameters

    @functools.wraps(func)
    async def wrapper(*args, current_user: Any = Depends(_get_current_user), **kwargs):
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
        async def wrapper(*args, current_user: Any = Depends(_get_current_user), **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="未认证")
            if _role_handler is None:
                raise HTTPException(status_code=500, detail="未配置角色检查回调，请调用 set_role_handler()")
            if not await _role_handler(kwargs.get("_request"), current_user, list(roles)):
                raise HTTPException(status_code=403, detail=f"需要角色: {', '.join(roles)}")
            return await base(*args, **kwargs)

        _inject_dependency(wrapper, "current_user", Any, Depends(_get_current_user))
        wrapper._auth_required = True
        return wrapper
    return decorator


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


# ============================================================
#  事务支持
# ============================================================

def transaction(func: Callable) -> Callable:
    """事务装饰器 — 在数据库事务中执行路由

    装饰的路由函数会自动在事务内执行，异常时自动回滚。
    需要 mybatis 连接模块已初始化。
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from .mybatis.connection import get_database
        db = get_database()
        async with db.transaction():
            return await func(*args, **kwargs)
    return wrapper


# ============================================================
#  控制器装饰器（统一处理所有 HTTP 方法）
# ============================================================

def _register_controller(method: str, path: str, name: str | None = None):
    """通用控制器注册内部方法"""
    registry_key = _METHOD_REGISTRY_KEYS[method]

    def decorator(func: Callable) -> Callable:
        nonlocal name
        if name is None:
            name = func.__name__
        oven.pancake_other["path"][name] = path
        oven.pancake_dough[registry_key][name] = func
        logger.info(f"{registry_key} {name} 已加入库")
        return func
    return decorator


def get_controller(path: str, name: str = None) -> Callable:
    """GET 控制器装饰器"""
    return _register_controller("GET", path, name)


def post_controller(path: str, name: str = None) -> Callable:
    """POST 控制器装饰器"""
    return _register_controller("POST", path, name)


def put_controller(path: str, name: str = None) -> Callable:
    """PUT 控制器装饰器"""
    return _register_controller("PUT", path, name)


def delete_controller(path: str, name: str = None) -> Callable:
    """DELETE 控制器装饰器"""
    return _register_controller("DELETE", path, name)


def patch_controller(path: str, name: str = None) -> Callable:
    """PATCH 控制器装饰器"""
    return _register_controller("PATCH", path, name)


# ---- 兼容旧接口 ----

def post_auto_controller(path: str, name: str = None) -> Callable:
    """POST 自动填充参数控制器（向后兼容）"""
    return _register_controller("POST", path, name)


def get_auto_controller(path: str, name: str = None) -> Callable:
    """GET 自动填充参数控制器（向后兼容）"""
    return _register_controller("GET", path, name)


# ============================================================
#  Web 服务主类
# ============================================================

class Main(InitAction):

    init_order: int = 50
    build_order: int = 50

    def __init__(self):
        # 初始化所有 HTTP 方法的控制器注册表
        for key in _METHOD_REGISTRY_KEYS.values():
            oven.pancake_dough[key] = {}
        oven.pancake_other["path"] = {}

        self.service_title: str = oven.pancake_yaml.get("service.title", "Pancake")
        self.service_version: str = oven.pancake_yaml.get("service.version", "0.1.0")
        self.service_host: str = oven.pancake_yaml.get("service.host", "127.0.0.1")
        self.service_port: int = int(oven.pancake_yaml.get("service.port", 8080))
        self.app: FastAPI = FastAPI(title=self.service_title, version=self.service_version)

    @staticmethod
    def check():
        pass

    def build(self):
        for method, registry_key in _METHOD_REGISTRY_KEYS.items():
            for name, func in oven.pancake_dough.get(registry_key, {}).items():
                path = oven.pancake_other["path"].get(name)
                if path:
                    self.app.add_api_route(path, func, methods=[method])

    def loop_method(self):
        logger.info(f"启动服务 {self.service_title}，监听地址 {self.service_host}:{self.service_port}")
        uvicorn.run(self.app, host=self.service_host, port=self.service_port)
        logger.info("服务启动成功")


# ============================================================
#  注册到 oven，使 embed 自动注入到 builtins
# ============================================================

# 控制器装饰器
oven.muffin_flour["get_controller"] = get_controller
oven.muffin_flour["post_controller"] = post_controller
oven.muffin_flour["put_controller"] = put_controller
oven.muffin_flour["delete_controller"] = delete_controller
oven.muffin_flour["patch_controller"] = patch_controller

# 认证 / 授权
oven.muffin_flour["auth_required"] = auth_required
oven.muffin_flour["role_required"] = role_required
oven.muffin_flour["set_auth_handler"] = set_auth_handler
oven.muffin_flour["set_role_handler"] = set_role_handler

# 事务
oven.muffin_flour["transaction"] = transaction
