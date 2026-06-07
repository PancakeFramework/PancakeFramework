# Pancake Framework

> A decorator-driven Python web framework with Spring-inspired IoC, MyBatis-style ORM, and AI workflow integration.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/pancake_framework?style=flat-square&color=blue)
![CI](https://img.shields.io/github/actions/workflow/status/Drayee/PancakeFramework/ci.yml?style=flat-square&label=CI)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-009688?style=flat-square&logo=fastapi&logoColor=white)

</div>

[中文文档](./README_CN.md)

## Features

- **Dough IoC System** — Spring-inspired Bean container with full lifecycle (`on_init` → `on_start` → `on_stop` → `on_destroy`)
- **Decorator-Driven** — `@Singleton`, `@Prototype`, `@Lazy`, `@DependsOn`, `@Import`, `@inject`
- **Async First** — All lifecycle methods support `async def`, DoughFactory handles sync/async transparently
- **Zero Import** — All decorators and services auto-injected into builtins
- **Base Classes** — `Configuration` (bean factory), `Service`, `Struct` (dataclass + Dough), `Function`
- **MyBatis Plus ORM** — Async ORM with CRUD, `@Select`/`@Insert`, dynamic SQL, chain queries
- **FastAPI Web** — Controllers, filter chain (Spring Security-style), auth, middleware, WebSocket
- **AI Module** — Unified LLM client (OpenAI/DeepSeek/Gemini/Ollama), memory, RAG
- **Redis Cache** — `@cached` with anti-penetration/avalanche/breakdown protection
- **Message Queue** — Event-driven with SimpleBroker and RedisBroker
- **Plugin System** — Auto-discovery, init-order control, external plugin dirs

## Quick Start

```bash
pip install pancake_framework
pancake create myapp && cd myapp
pancake run
```

Server starts at `http://127.0.0.1:8080`. Health check at `/health`.

## Dough IoC System

The core of Pancake is the **Dough** system — a Spring-inspired IoC container.

### Bean Lifecycle

```
__init__()  →  on_init()  →  on_start()  →  [running]  →  on_stop()  →  on_destroy()
   构造        @PostConstruct    就绪                        停止         @PreDestroy
```

### Scopes

| Scope | Decorator | Description |
|-------|-----------|-------------|
| Singleton | `@Singleton` | One instance per factory (default) |
| Prototype | `@Prototype` | New instance every resolve |
| Lazy | `@Lazy` | Created on first access |

### Example

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

### Decorators

| Decorator | Target | Description |
|-----------|--------|-------------|
| `@DoughDecorator` | Class | Mark class as Bean |
| `@Singleton` | Class | Singleton scope |
| `@Prototype` | Class | Prototype scope |
| `@Lazy` | Class | Lazy initialization |
| `@DependsOn("A", "B")` | Class | Declare dependencies |
| `@Import(ExternalCls)` | Class | Auto-register external classes |
| `@Maker` | Method | Mark method return as Bean |
| `@noMaker` | Method | Exclude method from auto-registration |
| `@inject` | Function | Auto-inject dependencies from factory |
| `@Config` | Class | Inject fields from settings |

## Documentation

| Module | Description |
|--------|-------------|
| [CLI](docs/cli.md) | Command-line tools |
| [Web](docs/web.md) | Controllers, filter chain, auth, middleware, WebSocket |
| [MyBatis ORM](docs/mybatis.md) | Mappers, CRUD, chain queries, dynamic SQL |
| [AI](docs/ai.md) | LLM client, memory, RAG |
| [Redis](docs/redis.md) | Cache, data structures, distributed locks |
| [Config](docs/config.md) | YAML/XML/env configuration |
| [Plugins](docs/plugin.md) | Plugin system and built-in plugins |
| [Messaging](docs/messaging.md) | Event-driven message queue |
| [Remote](docs/remote.md) | HTTP and gRPC remote calls |
| [Security](docs/security.md) | Password hashing, API key, CSRF, OAuth2, sessions |

## Optional Dependencies

```bash
pip install pancake_framework[ai]          # AI module
pip install pancake_framework[langgraph]   # LangGraph workflow
pip install pancake_framework[redis]       # Redis cache & messaging
pip install pancake_framework[grpc]        # gRPC remote calls
pip install pancake_framework[cui]         # Click CLI commands
pip install pancake_framework[gui]         # Flet GUI
pip install pancake_framework[all]         # All optional deps
```

## Architecture

```
pancake/
├── dough.py           # Dough base class, Scope enum, DoughMeta metaclass
├── registry.py        # Global class & decorator registry
├── decorators.py      # @Singleton, @Prototype, @Lazy, @inject, etc.
├── settings.py        # Centralized configuration management
├── run.py             # Startup pipeline
├── base/              # Configuration, Function, Service, Struct
├── factory/           # DoughFactory — Bean lifecycle management
├── builder/           # Build pipeline, plugin loader, source loader
├── ovenware/          # Broker (message queue)
├── oven/              # Legacy registry (backward compat for plugins)
├── resource/          # YAML/JSON/XML config loaders
└── tool/              # Utilities
```

## Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## License

MIT
