"""
Langgraph 核心引擎
支持自定义 State 类型、异步节点、图验证、错误处理

配置项（YAML 或 XML）：
  langgraph.state_fields: null        # 自定义 State 字段，如 {messages: str, context: dict}
  langgraph.enable_graph: true        # 是否编译图（false 则仅注册节点，不编译）
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Optional

from pancake import oven
from ..inject import _get_param_types

logger = logging.getLogger(__name__)


class Main(InitAction):
    """Langgraph 主类 - 构建并编译状态图"""

    init_order = 3  # 在 redis 之后，web 之前

    def __init__(self):
        self.app = None
        self.workflow = None
        self._state_class = None

        oven.pancake_dough.setdefault("langgraph_node", {})
        oven.pancake_dough.setdefault("langgraph_edge", {})
        oven.pancake_other.setdefault("first_node", [])
        oven.pancake_other.setdefault("last_node", [])
        oven.pancake_other.setdefault("langgraph_map", {})
        oven.pancake_other.setdefault("langgraph_edge_info", {})

    def _build_state_class(self):
        """构建 State 类型（支持自定义字段）"""
        try:
            from typing import TypedDict, Annotated, Sequence
            from langgraph.graph.message import add_messages
            from langchain_core.messages import BaseMessage

            # 检查用户是否自定义了 State 字段
            custom_fields = oven.pancake_yaml.get("langgraph.state_fields")

            if custom_fields and isinstance(custom_fields, dict):
                # 用户自定义 State
                annotations = {}
                for field_name, field_type_str in custom_fields.items():
                    if field_type_str == "messages":
                        annotations[field_name] = Annotated[Sequence[BaseMessage], add_messages]
                    elif field_type_str == "str":
                        annotations[field_name] = str
                    elif field_type_str == "dict":
                        annotations[field_name] = dict
                    elif field_type_str == "list":
                        annotations[field_name] = list
                    else:
                        annotations[field_name] = Any

                self._state_class = TypedDict("State", annotations)
                logger.info(f"使用自定义 State: {list(custom_fields.keys())}")
            else:
                # 默认 State（仅 messages）
                class State(TypedDict):
                    messages: Annotated[Sequence[BaseMessage], add_messages]

                self._state_class = State
                logger.info("使用默认 State (messages)")

            return True

        except ImportError:
            logger.info("langgraph/langchain_core 未安装，跳过 State 构建")
            return False

    def build(self):
        """编译状态图"""
        if not oven.pancake_yaml.get("langgraph.enable_graph", True):
            logger.info("langgraph 图编译已禁用")
            return

        nodes = oven.pancake_dough.get("langgraph_node", {})
        if not nodes:
            logger.info("无 langgraph 节点，跳过图编译")
            return

        # 验证图结构
        issues = self._validate_graph(nodes)
        if issues:
            for issue in issues:
                logger.warning(f"图验证: {issue}")

        try:
            from langgraph.graph import StateGraph, END

            if not self._build_state_class():
                return

            self.workflow = StateGraph(self._state_class)

            # 注册节点
            for name, func in nodes.items():
                self.workflow.add_node(name, func)
                logger.debug(f"注册节点: {name}")

            # 设置入口节点
            first_nodes = oven.pancake_other.get("first_node", [])
            if not first_nodes:
                logger.warning("未设置入口节点(first_last=True)，图无法运行")
            else:
                for first_node in first_nodes:
                    if first_node in nodes:
                        self.workflow.set_entry_point(first_node)
                        logger.debug(f"入口节点: {first_node}")
                    else:
                        logger.warning(f"入口节点 '{first_node}' 未注册，已忽略")

            # 设置出口节点（自动连接到 END）
            last_nodes = oven.pancake_other.get("last_node", [])
            for last_node in last_nodes:
                if last_node in nodes:
                    self.workflow.add_edge(last_node, END)
                    logger.debug(f"出口节点: {last_node} -> END")

            # 注册边
            edge_info = oven.pancake_other.get("langgraph_edge_info", {})
            for name, func in oven.pancake_dough.get("langgraph_edge", {}).items():
                info = edge_info.get(name, {})
                from_node = info.get("from_node")
                route_map = info.get("route_map")

                if from_node and from_node in nodes:
                    if route_map:
                        self.workflow.add_conditional_edges(from_node, func, route_map)
                        logger.debug(f"条件边: {from_node} -> {route_map}")
                    else:
                        self.workflow.add_edge(from_node, func)
                        logger.debug(f"普通边: {from_node} -> {func.__name__}")

            # 编译图
            if first_nodes:
                self.app = self.workflow.compile()
                logger.info(f"Langgraph 图编译完成 ({len(nodes)} 个节点)")
            else:
                logger.info("Langgraph 图未编译（缺少入口节点）")

        except ImportError as e:
            logger.info(f"langgraph 包未安装，跳过图编译: {e}")
        except Exception as e:
            logger.error(f"Langgraph 图编译失败: {e}")

        # 保存到 oven
        oven.pancake_other["langgraph_app"] = self.app
        oven.pancake_other["get_graph"] = self._get_graph

    def _validate_graph(self, nodes: dict) -> list[str]:
        """验证图结构，返回问题列表"""
        issues = []

        first_nodes = oven.pancake_other.get("first_node", [])
        last_nodes = oven.pancake_other.get("last_node", [])

        # 检查入口节点是否存在
        for n in first_nodes:
            if n not in nodes:
                issues.append(f"入口节点 '{n}' 未注册")

        # 检查出口节点是否存在
        for n in last_nodes:
            if n not in nodes:
                issues.append(f"出口节点 '{n}' 未注册")

        # 检查边的源节点是否存在
        edge_info = oven.pancake_other.get("langgraph_edge_info", {})
        for name, info in edge_info.items():
            from_node = info.get("from_node")
            if from_node and from_node not in nodes:
                issues.append(f"边 '{name}' 的源节点 '{from_node}' 未注册")

        return issues

    def _get_graph(self):
        """获取图的可视化（返回 Mermaid 文本）"""
        if not self.app:
            logger.warning("图未编译，无法获取可视化")
            return None

        try:
            graph = self.app.get_graph(xray=True)
            # 优先尝试 Mermaid 文本
            try:
                return graph.draw_mermaid()
            except Exception:
                pass
            # 降级到 ASCII
            try:
                return graph.draw_ascii()
            except Exception:
                pass
            return str(graph)
        except Exception as e:
            logger.error(f"获取图可视化失败: {e}")
            return None

    def loop_method(self):
        """运行时钩子"""
        if self.app:
            logger.info("Langgraph 图已就绪，可通过 langgraph_app 调用")


def langgraph_node(name: str = None, first_last: bool = None):
    """
    注册 langgraph 节点

    Args:
        name: 节点名称（默认使用函数名）
        first_last: True=入口节点, False=出口节点, None=中间节点

    使用示例：
        @langgraph_node(first_last=True)
        async def start_node(state):
            return {"messages": [HumanMessage(content="开始")]}

        @langgraph_node()
        async def process_node(state, config):
            return {"result": "处理完成"}
    """
    def decorator(func):
        nonlocal name
        if name is None:
            name = func.__name__

        # 注册节点
        oven.pancake_dough.setdefault("langgraph_node", {})[name] = func

        # 设置入口/出口
        if first_last is not None:
            if first_last:
                oven.pancake_other.setdefault("first_node", []).append(name)
            else:
                oven.pancake_other.setdefault("last_node", []).append(name)

        # 获取参数类型用于依赖注入
        param_types = list(_get_param_types(func).keys())
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def wrapper(state, **kwargs):
            """节点包装器，支持依赖注入和错误处理"""
            try:
                # 构建注入参数
                inject_kwargs = {}
                langgraph_map = oven.pancake_other.get("langgraph_map", {})

                for param in param_types:
                    if param in ("state",):
                        inject_kwargs[param] = state
                    elif param in kwargs:
                        # 从 langgraph 传入的参数（config 等）
                        inject_kwargs[param] = kwargs[param]
                    elif param in langgraph_map:
                        # 从共享 map 获取
                        inject_kwargs[param] = langgraph_map[param]
                    else:
                        inject_kwargs[param] = None

                # 调用原函数
                if is_async:
                    result = await func(**inject_kwargs)
                else:
                    result = func(**inject_kwargs)

                # 存储返回值到共享 map
                if result is not None:
                    if isinstance(result, dict):
                        oven.pancake_other.setdefault("langgraph_map", {}).update(result)
                    else:
                        oven.pancake_other.setdefault("langgraph_map", {})[name] = result

                return result

            except Exception as e:
                logger.error(f"节点 '{name}' 执行失败: {e}")
                raise

        # 保留元信息
        wrapper._node_name = name
        wrapper._is_first = first_last is True
        wrapper._is_last = first_last is False

        return wrapper
    return decorator


def langgraph_edge(from_node: str = None, route_map: dict = None, name: str = None):
    """
    注册 langgraph 边（支持条件路由）

    Args:
        from_node: 源节点名称
        route_map: 条件路由映射 {条件值: 目标节点}
        name: 边名称（默认使用函数名）

    使用示例：
        # 普通边（在 langgraph_node 中通过 first_last 控制即可）

        # 条件边
        @langgraph_edge(from_node="check", route_map={"ok": "process", "fail": "error"})
        def route_on_check(state):
            return "ok" if state.get("valid") else "fail"
    """
    def decorator(func):
        nonlocal name
        if name is None:
            name = func.__name__

        # 注册边
        oven.pancake_dough.setdefault("langgraph_edge", {})[name] = func
        oven.pancake_other.setdefault("langgraph_edge_info", {})[name] = {
            "from_node": from_node,
            "route_map": route_map,
        }

        # 获取参数类型
        param_types = list(_get_param_types(func).keys())

        @functools.wraps(func)
        def wrapper(state):
            """边包装器，支持依赖注入"""
            try:
                inject_kwargs = {}
                langgraph_map = oven.pancake_other.get("langgraph_map", {})

                for param in param_types:
                    if param == "state":
                        inject_kwargs[param] = state
                    elif param in langgraph_map:
                        inject_kwargs[param] = langgraph_map[param]
                    else:
                        inject_kwargs[param] = None

                return func(**inject_kwargs)

            except Exception as e:
                logger.error(f"边 '{name}' 执行失败: {e}")
                raise

        wrapper._edge_name = name
        wrapper._from_node = from_node
        wrapper._route_map = route_map

        return wrapper
    return decorator


