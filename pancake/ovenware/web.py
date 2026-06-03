"""
Web 服务插件
提供 Web 服务的构建和运行功能，支持完整 HTTP 方法、认证授权、事务、中间件、参数校验
"""

import asyncio
import functools
import inspect
import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Depends, HTTPException, Request, Response, WebSocket
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
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
        async def wrapper(*args, request: Request, current_user: Any = Depends(_get_current_user), **kwargs):
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
#  中间件 / 拦截器
# ============================================================

_middleware_registry: list[dict] = []


def middleware(order: int = 0):
    """中间件装饰器 — 注册请求/响应拦截器

    装饰的函数签名为 async def handler(request: Request, call_next) -> Response

    用法:
        @middleware(order=10)
        async def log_request(request: Request, call_next):
            start = time.time()
            response = await call_next(request)
            logger.info(f"{request.method} {request.url.path} {time.time()-start:.3f}s")
            return response
    """
    def decorator(func: Callable) -> Callable:
        _middleware_registry.append({"func": func, "order": order})
        _middleware_registry.sort(key=lambda x: x["order"])
        logger.info(f"中间件 {func.__name__} 已注册 (order={order})")
        return func
    return decorator


# ============================================================
#  参数校验
# ============================================================

def validate(**validators: Callable):
    """参数校验装饰器 — 对控制器参数进行校验

    用法:
        @post_controller("/users")
        @validate(age=lambda v: 0 < v < 200, name=lambda v: len(v) > 0)
        async def create_user(name: str, age: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for param_name, checker in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    try:
                        if not checker(value):
                            raise HTTPException(
                                status_code=422,
                                detail=f"参数校验失败: {param_name}={value}"
                            )
                    except HTTPException:
                        raise
                    except Exception as e:
                        raise HTTPException(
                            status_code=422,
                            detail=f"参数校验异常: {param_name} — {e}"
                        )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
#  指标统计
# ============================================================

_metrics = {
    "request_count": 0,
    "error_count": 0,
    "total_duration": 0.0,
    "by_path": defaultdict(lambda: {"count": 0, "errors": 0, "duration": 0.0}),
}


def _record_metric(path: str, method: str, status_code: int, duration: float):
    """记录请求指标"""
    _metrics["request_count"] += 1
    _metrics["total_duration"] += duration
    if status_code >= 400:
        _metrics["error_count"] += 1

    key = f"{method} {path}"
    _metrics["by_path"][key]["count"] += 1
    _metrics["by_path"][key]["duration"] += duration
    if status_code >= 400:
        _metrics["by_path"][key]["errors"] += 1


def get_metrics() -> dict:
    """获取指标快照"""
    result = dict(_metrics)
    result["by_path"] = dict(_metrics["by_path"])
    result["avg_duration"] = (
        _metrics["total_duration"] / _metrics["request_count"]
        if _metrics["request_count"] > 0 else 0.0
    )
    return result


# ============================================================
#  限流
# ============================================================

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def rate_limit(times: int, seconds: int = 60):
    """限流装饰器 — 限制指定时间窗口内的请求次数

    基于客户端 IP 的滑动窗口限流，内存实现。

    用法:
        @get_controller("/api/data")
        @rate_limit(times=100, seconds=60)
        async def get_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{func.__name__}:{client_ip}"
            now = time.time()

            # 清理过期记录
            _rate_limit_store[key] = [
                t for t in _rate_limit_store[key] if now - t < seconds
            ]

            if len(_rate_limit_store[key]) >= times:
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请 {seconds} 秒后重试"
                )

            _rate_limit_store[key].append(now)
            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator


# ============================================================
#  WebSocket 控制器
# ============================================================

_websocket_registry: dict[str, Callable] = {}
_websocket_paths: dict[str, str] = {}


def websocket_controller(path: str, name: str = None):
    """WebSocket 控制器装饰器

    装饰的函数签名为 async def handler(websocket: WebSocket)

    用法:
        @websocket_controller("/ws/chat")
        async def chat(websocket: WebSocket):
            await websocket.accept()
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"Echo: {data}")
    """
    def decorator(func: Callable) -> Callable:
        nonlocal name
        if name is None:
            name = func.__name__
        _websocket_registry[name] = func
        _websocket_paths[name] = path
        logger.info(f"WebSocket {name} 已注册: {path}")
        return func
    return decorator


# ============================================================
#  控制器装饰器（统一处理所有 HTTP 方法）
# ============================================================

def _register_controller(method: str, path: str, name: str | None = None, tags: list[str] | None = None):
    """通用控制器注册内部方法"""
    registry_key = _METHOD_REGISTRY_KEYS[method]

    def decorator(func: Callable) -> Callable:
        nonlocal name
        if name is None:
            name = func.__name__
        oven.pancake_other["path"][name] = path
        oven.pancake_dough[registry_key][name] = func
        if tags:
            oven.pancake_other.setdefault("tags", {})[name] = tags
        logger.info(f"{registry_key} {name} 已加入库")
        return func
    return decorator


def get_controller(path: str, name: str = None, tags: list[str] = None) -> Callable:
    """GET 控制器装饰器"""
    return _register_controller("GET", path, name, tags)


def post_controller(path: str, name: str = None, tags: list[str] = None) -> Callable:
    """POST 控制器装饰器"""
    return _register_controller("POST", path, name, tags)


def put_controller(path: str, name: str = None, tags: list[str] = None) -> Callable:
    """PUT 控制器装饰器"""
    return _register_controller("PUT", path, name, tags)


def delete_controller(path: str, name: str = None, tags: list[str] = None) -> Callable:
    """DELETE 控制器装饰器"""
    return _register_controller("DELETE", path, name, tags)


def patch_controller(path: str, name: str = None, tags: list[str] = None) -> Callable:
    """PATCH 控制器装饰器"""
    return _register_controller("PATCH", path, name, tags)


def page_controller(path: str, template: str, name: str = None, tags: list[str] = None) -> Callable:
    """页面控制器装饰器 — 渲染 Jinja2 模板返回 HTML

    装饰的函数返回 dict，作为模板的 context 变量。

    用法:
        @page_controller("/home", template="home.html")
        async def home():
            return {"title": "首页", "message": "Hello"}

        @page_controller("/users", template="users.html")
        async def users_page():
            users = await UserMapper().select_list()
            return {"users": users}
    """
    def decorator(func: Callable) -> Callable:
        nonlocal name
        if name is None:
            name = func.__name__
        oven.pancake_other["path"][name] = path
        oven.pancake_dough.setdefault("PageController", {})[name] = {
            "func": func,
            "template": template,
        }
        if tags:
            oven.pancake_other.setdefault("tags", {})[name] = tags
        logger.info(f"PageController {name} 已加入库: {path} -> {template}")
        return func
    return decorator


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
        oven.pancake_dough["PageController"] = {}
        oven.pancake_other["path"] = {}

        self.service_title: str = oven.pancake_yaml.get("service.title", "Pancake")
        self.service_version: str = oven.pancake_yaml.get("service.version", "0.1.0")
        self.service_host: str = oven.pancake_yaml.get("service.host", "127.0.0.1")
        self.service_port: int = int(oven.pancake_yaml.get("service.port", 8080))
        self.service_description: str = oven.pancake_yaml.get("service.description", "")

        # API 文档配置
        docs_enabled = oven.pancake_yaml.get("service.docs_enabled", True)
        docs_url = "/docs" if docs_enabled else None
        redoc_url = "/redoc" if docs_enabled else None
        openapi_url = "/openapi.json" if docs_enabled else None

        self.app: FastAPI = FastAPI(
            title=self.service_title,
            version=self.service_version,
            description=self.service_description,
            docs_url=docs_url,
            redoc_url=redoc_url,
            openapi_url=openapi_url,
        )

        # 模板和静态文件配置
        self.template_dir = oven.pancake_yaml.get("service.template_dir", os.path.join("src", "templates"))
        self.static_dir = oven.pancake_yaml.get("service.static_dir", os.path.join("src", "static"))
        self.static_url = oven.pancake_yaml.get("service.static_url", "/static")

        # 初始化 Jinja2 环境
        self._jinja_env = None
        try:
            from jinja2 import Environment, FileSystemLoader
            template_path = Path(self.template_dir)
            if template_path.is_absolute():
                abs_template_dir = str(template_path)
            else:
                abs_template_dir = str(Path(os.getcwd()) / template_path)
            if os.path.isdir(abs_template_dir):
                self._jinja_env = Environment(loader=FileSystemLoader(abs_template_dir))
                logger.info(f"Jinja2 模板目录: {abs_template_dir}")
            else:
                logger.warning(f"模板目录不存在: {abs_template_dir}，页面渲染功能不可用")
        except ImportError:
            logger.warning("jinja2 未安装，页面渲染功能不可用，请运行: pip install jinja2")

    @staticmethod
    def check():
        pass

    def build(self):
        # 挂载静态文件目录
        static_path = Path(self.static_dir)
        if static_path.is_absolute():
            abs_static_dir = str(static_path)
        else:
            abs_static_dir = str(Path(os.getcwd()) / static_path)
        if os.path.isdir(abs_static_dir):
            self.app.mount(self.static_url, StaticFiles(directory=abs_static_dir), name="static")
            logger.info(f"静态文件已挂载: {self.static_url} -> {abs_static_dir}")
        else:
            logger.info(f"静态目录不存在: {abs_static_dir}，跳过挂载")

        # 注册中间件
        for mw in _middleware_registry:
            self.app.add_middleware(BaseHTTPMiddleware, dispatch=mw["func"])
            logger.info(f"中间件 {mw['func'].__name__} 已挂载")

        # 注册指标中间件
        metrics_enabled = oven.pancake_yaml.get("service.metrics_enabled", True)
        if metrics_enabled:
            @self.app.middleware("http")
            async def metrics_middleware(request: Request, call_next):
                start = time.time()
                response = await call_next(request)
                duration = time.time() - start
                _record_metric(request.url.path, request.method, response.status_code, duration)
                return response

            @self.app.get("/health")
            async def health_check() -> dict:
                return {"status": "ok", "title": self.service_title, "version": self.service_version}

            @self.app.get("/metrics")
            async def metrics_endpoint() -> dict:
                return get_metrics()
        else:
            @self.app.get("/health")
            async def health_check() -> dict:
                return {"status": "ok", "title": self.service_title, "version": self.service_version}

        # 注册控制器路由
        tags_map = oven.pancake_other.get("tags", {})
        for method, registry_key in _METHOD_REGISTRY_KEYS.items():
            for name, func in oven.pancake_dough.get(registry_key, {}).items():
                path = oven.pancake_other["path"].get(name)
                if path:
                    tags = tags_map.get(name)
                    self.app.add_api_route(path, func, methods=[method], tags=tags)

        # 注册 WebSocket 路由
        for name, func in _websocket_registry.items():
            path = _websocket_paths.get(name)
            if path:
                self.app.websocket(path)(func)
                logger.info(f"WebSocket 路由 {name} 已挂载: {path}")

        # 注册页面控制器路由（Jinja2 模板渲染）
        page_controllers = oven.pancake_dough.get("PageController", {})
        tags_map = oven.pancake_other.get("tags", {})
        for name, info in page_controllers.items():
            path = oven.pancake_other["path"].get(name)
            if path:
                func = info["func"]
                template_name = info["template"]
                tags = tags_map.get(name)

                def _make_page_handler(f, tpl):
                    async def page_handler(**kwargs):
                        context = await f(**kwargs) if asyncio.iscoroutinefunction(f) else f(**kwargs)
                        if not isinstance(context, dict):
                            context = {}
                        if self._jinja_env:
                            template = self._jinja_env.get_template(tpl)
                            html = template.render(**context)
                            return HTMLResponse(content=html)
                        else:
                            return HTMLResponse(content=f"<h1>模板引擎未安装</h1><p>请安装 jinja2: pip install jinja2</p>")
                    functools.wraps(f)(page_handler)
                    return page_handler

                handler = _make_page_handler(func, template_name)
                self.app.add_api_route(path, handler, methods=["GET"], tags=tags)
                logger.info(f"PageController 路由 {name} 已挂载: {path} -> {template_name}")

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
oven.muffin_flour["page_controller"] = page_controller

# 认证 / 授权
oven.muffin_flour["auth_required"] = auth_required
oven.muffin_flour["role_required"] = role_required
oven.muffin_flour["set_auth_handler"] = set_auth_handler
oven.muffin_flour["set_role_handler"] = set_role_handler

# 事务
oven.muffin_flour["transaction"] = transaction

# 中间件 / 校验
oven.muffin_flour["middleware"] = middleware
oven.muffin_flour["validate"] = validate

# 限流
oven.muffin_flour["rate_limit"] = rate_limit

# WebSocket
oven.muffin_flour["websocket_controller"] = websocket_controller
