"""
Web 服务主类
FastAPI 初始化、Filter Chain 构建、路由注册、uvicorn 启动
"""

import asyncio
import functools
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

from pancake import oven
from pancake.ovenware import InitAction

logger = logging.getLogger(__name__)


class Main(InitAction):

    init_order: int = 50
    build_order: int = 50

    def __init__(self):
        from pancake import settings

        # 初始化所有 HTTP 方法的控制器注册表
        from .controller import _METHOD_REGISTRY_KEYS
        for key in _METHOD_REGISTRY_KEYS.values():
            oven.pancake_dough[key] = {}
        oven.pancake_dough["PageController"] = {}
        oven.pancake_other["path"] = {}

        # 读取配置（优先 YAML，回退到 settings 默认值）
        self.service_title: str = oven.pancake_yaml.get("service.title", settings.get("service.title"))
        self.service_version: str = oven.pancake_yaml.get("service.version", settings.get("service.version"))
        self.service_host: str = oven.pancake_yaml.get("service.host", settings.get("service.host"))
        self.service_port: int = int(oven.pancake_yaml.get("service.port", settings.get("service.port")))
        self.service_description: str = oven.pancake_yaml.get("service.description", settings.get("service.description"))

        # API 文档配置
        docs_enabled = oven.pancake_yaml.get("service.docs_enabled", settings.get("service.docs_enabled"))
        docs_url = "/docs" if docs_enabled else None
        redoc_url = "/redoc" if docs_enabled else None
        openapi_url = "/openapi.json" if docs_enabled else None

        # 生命周期管理：执行各插件注册的 startup/shutdown 钩子
        @asynccontextmanager
        async def lifespan(app):
            for hook in oven.muffin_egg.get("on_startup", []):
                await hook()
            yield
            for hook in oven.muffin_egg.get("on_shutdown", []):
                await hook()

        self.app: FastAPI = FastAPI(
            title=self.service_title,
            version=self.service_version,
            description=self.service_description,
            docs_url=docs_url,
            redoc_url=redoc_url,
            openapi_url=openapi_url,
            lifespan=lifespan,
        )

        # 模板和静态文件配置
        self.template_dir = oven.pancake_yaml.get("service.template_dir",
                                                   settings.get_path("template_dir") or os.path.join("src", "templates"))
        self.static_dir = oven.pancake_yaml.get("service.static_dir",
                                                 settings.get_path("static_dir") or os.path.join("src", "static"))
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
        from pancake import settings
        from .controller import _METHOD_REGISTRY_KEYS, _auto_annotate_body
        from .filter import _filter_registry, MetricsFilter
        from .websocket import _websocket_registry, _websocket_paths

        # 按配置启用内置 MetricsFilter
        metrics_enabled = oven.pancake_yaml.get("service.metrics_enabled", settings.get("service.metrics_enabled"))
        if metrics_enabled:
            # 检查是否已注册（避免重复）
            if not any(f["name"] == "metrics" for f in _filter_registry):
                MetricsFilter()

        # 注册 Filter Chain 中间件
        filters = list(_filter_registry)
        if filters:
            @self.app.middleware("http")
            async def filter_chain_middleware(request: Request, call_next):
                async def _run_chain(idx, req):
                    if idx >= len(filters):
                        return await call_next(req)
                    return await filters[idx]["func"](req, lambda r: _run_chain(idx + 1, r))
                return await _run_chain(0, request)

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

        # 健康检查端点
        @self.app.get("/health")
        async def health_check() -> dict:
            return {"status": "ok", "title": self.service_title, "version": self.service_version}

        # 指标端点
        if metrics_enabled:
            from .metrics import get_metrics
            @self.app.get("/metrics")
            async def metrics_endpoint() -> dict:
                return get_metrics()

        # 注册控制器路由
        tags_map = oven.pancake_other.get("tags", {})
        for method, registry_key in _METHOD_REGISTRY_KEYS.items():
            for name, func in oven.pancake_dough.get(registry_key, {}).items():
                path = oven.pancake_other["path"].get(name)
                if path:
                    tags = tags_map.get(name)
                    _auto_annotate_body(func)
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
