"""CUI 插件测试"""

import pytest
from unittest.mock import MagicMock
from pancake import oven
from pancake_cui.cui import (
    cui_command, cui_option, cui_argument,
    _CommandInfo, _make_click_callback,
)
from pancake_cui import Main


class TestCuiCommandDecorator:

    def test_register_command(self):
        # 清理
        old = oven.pancake_dough.get("CuiCommand", {}).copy()
        try:
            oven.pancake_dough["CuiCommand"] = {}

            @cui_command("test-cmd", help="测试命令")
            def test_cmd():
                pass

            assert "test-cmd" in oven.pancake_dough["CuiCommand"]
            info = oven.pancake_dough["CuiCommand"]["test-cmd"]
            assert info.name == "test-cmd"
            assert info.help == "测试命令"
        finally:
            oven.pancake_dough["CuiCommand"] = old

    def test_default_name_from_function(self):
        old = oven.pancake_dough.get("CuiCommand", {}).copy()
        try:
            oven.pancake_dough["CuiCommand"] = {}

            @cui_command()
            def my_function():
                pass

            assert "my-function" in oven.pancake_dough["CuiCommand"]
        finally:
            oven.pancake_dough["CuiCommand"] = old

    def test_command_with_params(self):
        import click
        old = oven.pancake_dough.get("CuiCommand", {}).copy()
        try:
            oven.pancake_dough["CuiCommand"] = {}

            @cui_command("greet")
            @cui_option("--name", "-n", default="World")
            def greet(name: str):
                pass

            info = oven.pancake_dough["CuiCommand"]["greet"]
            assert len(info.params) == 1
            assert isinstance(info.params[0], click.Option)
        finally:
            oven.pancake_dough["CuiCommand"] = old


class TestCuiOptionDecorator:

    def test_adds_option(self):
        import click

        @cui_option("--verbose", "-v", is_flag=True, help="详细输出")
        def func(verbose):
            pass

        assert hasattr(func, "_cui_params")
        assert len(func._cui_params) == 1
        assert isinstance(func._cui_params[0], click.Option)

    def test_multiple_options(self):
        @cui_option("--name", "-n")
        @cui_option("--count", "-c", type=int)
        def func(name, count):
            pass

        assert len(func._cui_params) == 2


class TestCuiArgumentDecorator:

    def test_adds_argument(self):
        import click

        @cui_argument("filename", type=click.Path())
        def func(filename):
            pass

        assert hasattr(func, "_cui_params")
        assert isinstance(func._cui_params[0], click.Argument)


class TestMakeClickCallback:

    def test_sync_function(self):
        info = _CommandInfo("test", lambda: "result")
        callback = _make_click_callback(info)
        result = callback()
        assert result == "result"

    def test_async_function(self):
        async def async_func():
            return "async_result"

        info = _CommandInfo("test", async_func)
        callback = _make_click_callback(info)
        result = callback()
        assert result == "async_result"


class TestMain:

    def test_active_when_cui_in_type(self):
        old_yaml = oven.pancake_yaml.copy()
        try:
            oven.pancake_yaml["client.type"] = ["cui", "web"]
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

    def test_inactive_default_is_web(self):
        """未配置 client.type 时默认 web，CUI 不激活"""
        old_yaml = oven.pancake_yaml.copy()
        try:
            # 不设置 client.type
            oven.pancake_yaml.pop("client.type", None)
            main = Main.__new__(Main)
            main.__init__()
            assert main._active is False
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)

    def test_build_creates_cli_group(self):
        import click
        old_yaml = oven.pancake_yaml.copy()
        old_dough = oven.pancake_dough.get("CuiCommand", {}).copy()
        try:
            oven.pancake_yaml["client.type"] = ["cui"]
            oven.pancake_dough["CuiCommand"] = {}

            @cui_command("hello")
            def hello():
                click.echo("hi")

            main = Main.__new__(Main)
            main.__init__()
            main.build()

            assert hasattr(main, "cli")
            assert isinstance(main.cli, click.Group)
        finally:
            oven.pancake_yaml.clear()
            oven.pancake_yaml.update(old_yaml)
            oven.pancake_dough["CuiCommand"] = old_dough
