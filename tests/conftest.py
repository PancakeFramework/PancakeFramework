"""共享 fixtures"""

import sys
import os
import pytest

# 确保 pancake 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def pancake_registry():
    """独立的 PancakeRegistry 实例"""
    from pancake.oven.pancake import PancakeRegistry
    return PancakeRegistry()


@pytest.fixture
def muffin_registry():
    """独立的 MuffinRegistry 实例"""
    from pancake.oven.muffin import MuffinRegistry
    return MuffinRegistry()


@pytest.fixture
def ioc_container():
    """独立的 IoCContainer 实例"""
    from pancake.ovenware.inject import IoCContainer
    return IoCContainer()
