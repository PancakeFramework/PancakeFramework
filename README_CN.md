# Pancake Framework

> 一个装饰器驱动的 Python Web 框架，集成 Spring 风格 IoC、MyBatis 风格 ORM 和 AI 工作流。

[English](./README.md)

## 特性

- **Dough IoC 系统** — Spring 风格 Bean 容器，完整生命周期（`on_init` → `on_start` → `on_stop` → `on_destroy`）
- **装饰器驱动** — `@Singleton`、`@Prototype`、`@Lazy`、`@DependsOn`、`@Import`、`@inject`
- **异步优先** — 所有生命周期方法支持 `async def`，DoughFactory 自动处理 sync/async
- **零 import** — 所有装饰器和服务自动注入 builtins，无需显式 import
- **基类体系** — `Configuration`（Bean 工厂）、`Service`、`Struct`（dataclass + Dough）、`Function`
- **MyBatis Plus ORM** — 异步 ORM，内置 CRUD、`@Select`/`@Insert`、动态 SQL、链式查询
- **FastAPI Web** — 控制器、过滤器链（类 Spring Security）、认证、中间件、WebSocket
- **AI 模块** — 统一 LLM 客户端 (OpenAI/DeepSeek/Gemini/Ollama)、记忆、RAG
- **Redis 缓存** — `@cached` 装饰器，防穿透/雪崩/击穿保护
- **消息队列** — 事件驱动，支持 SimpleBroker 和 RedisBroker
- **插件系统** — 自动发现加载，init_order 控制顺序，支持外部插件目录

## 快速开始

```bash
pip install pancake_framework
pancake create myapp && cd myapp
pancake run
```

服务启动在 `http://127.0.0.1:8080`，健康检查 `/health`。

## Dough IoC 系统

Pancake 的核心是 **Dough** 系统 — Spring 风格的 IoC 容器。

### Bean 生命周期

```
__init__()  →  on_init()  →  on_start()  →  [运行中]  →  on_stop()  →  on_destroy()
   构造        @PostConstruct    就绪                        停止         @PreDestroy
```

### 作用域

| 作用域 | 装饰器 | 说明 |
|--------|--------|------|
| 单例 | `@Singleton` | 每个工厂一个实例（默认） |
| 多例 | `@Prototype` | 每次获取创建新实例 |
| 懒加载 | `@Lazy` | 首次访问时创建 |

### 示例

```python
from pancake import Service, DoughFactory, DependsOn, inject, Singleton

@Singleton
@DependsOn("DatabaseService")
class UserService(Service):
    async def on_init(self):
        self.db = DoughFactory.get().resolve("DatabaseService")

    async def find_user(self, user_id: int):
        return await self.db.query(user_id)

class AppConfig(Configuration):
    def my_cache(self):
        return RedisCache()

    @noMaker
    def helper(self):
        return "not a bean"
```

### 装饰器一览

| 装饰器 | 目标 | 说明 |
|--------|------|------|
| `@DoughDecorator` | 类 | 标记类为 Bean |
| `@Singleton` | 类 | 单例作用域 |
| `@Prototype` | 类 | 多例作用域 |
| `@Lazy` | 类 | 懒加载 |
| `@DependsOn("A", "B")` | 类 | 声明依赖 |
| `@Import(ExternalCls)` | 类 | 自动注册外部类 |
| `@Maker` | 方法 | 标记方法返回值为 Bean |
| `@noMaker` | 方法 | 排除方法，不自动注册 |
| `@inject` | 函数 | 自动从工厂注入依赖 |
| `@Config` | 类 | 从配置注入字段 |

## 文档

| 模块 | 说明 |
|------|------|
| [CLI](docs/cn/cli.md) | 命令行工具 |
| [Web](docs/cn/web.md) | 控制器、过滤器链、认证、中间件、WebSocket |
| [MyBatis ORM](docs/cn/mybatis.md) | Mapper、CRUD、链式查询、动态 SQL |
| [AI](docs/cn/ai.md) | LLM 客户端、记忆、RAG |
| [Redis](docs/cn/redis.md) | 缓存、数据结构、分布式锁 |
| [配置](docs/cn/config.md) | YAML/XML/环境变量配置 |
| [插件](docs/cn/plugin.md) | 插件系统和内置插件 |
| [消息队列](docs/cn/messaging.md) | 事件驱动消息队列 |
| [远程调用](docs/cn/remote.md) | HTTP 和 gRPC 远程调用 |
| [安全](docs/cn/security.md) | 密码哈希、API Key、CSRF、OAuth2、会话管理 |

## 可选依赖

```bash
pip install pancake_framework[ai]          # AI 模块
pip install pancake_framework[langgraph]   # LangGraph 工作流
pip install pancake_framework[redis]       # Redis 缓存和消息队列
pip install pancake_framework[grpc]        # gRPC 远程调用
pip install pancake_framework[cui]         # Click CLI 命令
pip install pancake_framework[gui]         # Flet GUI
pip install pancake_framework[all]         # 全部可选依赖
```

## 项目结构

```
pancake/
├── dough.py           # Dough 基类、Scope 枚举、DoughMeta 元类
├── registry.py        # 全局类/装饰器注册表
├── decorators.py      # @Singleton、@Prototype、@Lazy、@inject 等
├── settings.py        # 集中配置管理
├── run.py             # 启动流水线
├── base/              # Configuration、Function、Service、Struct
├── factory/           # DoughFactory — Bean 生命周期管理
├── builder/           # 构建流水线、插件加载、源码加载
├── ovenware/          # Broker 消息队列
├── oven/              # 旧注册表（向后兼容外部插件）
├── resource/          # YAML/JSON/XML 配置加载器
└── tool/              # 工具类
```

## 测试

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## 开源协议

MIT
