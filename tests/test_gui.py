"""GUI 插件测试"""

import pytest
from pancake import oven
from pancake_gui.gui import (
    gui_page, gui_action,
    _PageInfo, _ActionInfo, _wrap_handler,
)
from pancake_gui import Main


class TestGuiPageDecorator:

    def test_register_page(self):
        old = oven.pancake_dough.get("GuiPage", {}).copy()
        try:
            oven.pancake_dough["GuiPage"] = {}

            @gui_page("/", title="首页")
            def home(page):
                pass

            assert "/" in oven.pancake_dough["GuiPage"]
            info = oven.pancake_dough["GuiPage"]["/"]
            assert info.route == "/"
            assert info.title == "首页"
        finally:
            oven.pancake_dough["GuiPage"] = old

    def test_default_route_from_function_name(self):
        old = oven.pancake_dough.get("GuiPage", {}).copy()
        try:
            oven.pancake_dough["GuiPage"] = {}

            @gui_page()
            def dashboard(page):
                pass

            assert "/dashboard" in oven.pancake_dough["GuiPage"]
        finally:
            oven.pancake_dough["GuiPage"] = old

    def test_multiple_pages(self):
        old = oven.pancake_dough.get("GuiPage", {}).copy()
        try:
            oven.pancake_dough["GuiPage"] = {}

            @gui_page("/")
            def home(page): pass

            @gui_page("/users")
            def users(page): pass

            assert len(oven.pancake_dough["GuiPage"]) == 2
        finally:
            oven.pancake_dough["GuiPage"] = old


class TestGuiActionDecorator:

    def test_register_action(self):
        old = oven.pancake_dough.get("GuiAction", {}).copy()
        try:
            oven.pancake_dough["GuiAction"] = {}

            @gui_action("refresh")
            def refresh(page):
                pass

            assert "refresh" in oven.pancake_dough["GuiAction"]
            info = oven.pancake_dough["GuiAction"]["refresh"]
            assert info.name == "refresh"
        finally:
            oven.pancake_dough["GuiAction"] = old

    def test_default_name_from_function(self):
        old = oven.pancake_dough.get("GuiAction", {}).copy()
        try:
            oven.pancake_dough["GuiAction"] = {}

            @gui_action()
            def load_data(page):
                pass

            assert "load_data" in oven.pancake_dough["GuiAction"]
        finally:
            oven.pancake_dough["GuiAction"] = old


class TestWrapHandler:

    def test_sync_handler(self):
        def handler(page):
            return "done"

        wrapped = _wrap_handler(handler)
        assert wrapped is handler  # 不包装同步函数

    def test_async_handler(self):
        async def handler(page):
            return "done"

        wrapped = _wrap_handler(handler)
        assert wrapped is not handler  # 包装异步函数


class TestMain:

    def test_active_when_gui_in_type(self):
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["client.type"] = ["gui"]
            main = Main.__new__(Main)
            main.__init__()
            assert main._active is True
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)

    def test_inactive_when_not_in_type(self):
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["client.type"] = ["web"]
            main = Main.__new__(Main)
            main.__init__()
            assert main._active is False
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)

    def test_config_port(self):
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["client.type"] = ["gui"]
            oven.pancake_yaml["client.gui.port"] = 9999
            main = Main.__new__(Main)
            main.__init__()
            assert main.port == 9999
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)

    def test_build_creates_handlers(self):
        old_yaml = oven.pancake_yaml.copy()
        old_pages = oven.pancake_dough.get("GuiPage", {}).copy()
        old_actions = oven.pancake_dough.get("GuiAction", {}).copy()
        try:
            oven.pancake_yaml["client.type"] = ["gui"]
            oven.pancake_dough["GuiPage"] = {}
            oven.pancake_dough["GuiAction"] = {}

            @gui_page("/")
            def home(page): pass

            @gui_action("test_action")
            def test_action(page): pass

            main = Main.__new__(Main)
            main.__init__()
            main.build()

            assert "/" in main._route_handlers
            assert "test_action" in main._action_handlers
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)
            oven.pancake_dough["GuiPage"] = old_pages
            oven.pancake_dough["GuiAction"] = old_actions

    def test_inactive_build_skips(self):
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["client.type"] = ["web"]
            main = Main.__new__(Main)
            main.__init__()
            main.build()
            # 不应创建 _route_handlers
            assert not hasattr(main, "_route_handlers")
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)
