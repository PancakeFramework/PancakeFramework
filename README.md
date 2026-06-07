# Pancake Framework

> A decorator-driven Python framework with Spring-inspired IoC, MyBatis-style ORM, and AI workflow integration.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/pancake_framework?style=flat-square&color=blue)
![CI](https://img.shields.io/github/actions/workflow/status/Drayee/PancakeFramework/ci.yml?style=flat-square&label=CI)

</div>

[中文文档](./README_CN.md)

## Features

- **Dough IoC System** — Spring-inspired Bean container with full lifecycle (`on_init` → `on_start` → `on_stop` → `on_destroy`)
- **Decorator-Driven** — `@Singleton`, `@Prototype`, `@Lazy`, `@DependsOn`, `@Import`, `@inject`
- **Async First** — All lifecycle methods support `async def`, DoughFactory handles sync/async transparently
- **Zero Import** — All decorators and services auto-injected into builtins
- **Base Classes** — `Configuration` (bean factory), `Service`, `Struct` (dataclass + Dough), `Function`
- **MyBatis Plus ORM** — Async ORM with CRUD, `@Select`/`@Insert`, dynamic SQL, chain queries
- **AI Module** — Unified LLM client (OpenAI/DeepSeek/Gemini/Ollama), memory, RAG
- **Redis Cache** — `@cached` with anti-penetration/avalanche/breakdown protection
- **Message Queue** — Event-driven with SimpleBroker and RedisBroker
- **Plugin System** — XML-based plugin management, auto pip install, `pancake plugin` CLI

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
| [MyBatis ORM](docs/mybatis.md) | Mappers, CRUD, chain queries, dynamic SQL |
| [AI](docs/ai.md) | LLM client, memory, RAG |
| [Redis](docs/redis.md) | Cache, data structures, distributed locks |
| [Config](docs/config.md) | YAML/XML/env configuration |
| [Plugins](docs/plugin.md) | Plugin system and built-in plugins |
| [Messaging](docs/messaging.md) | Event-driven message queue |
| [Remote](docs/remote.md) | HTTP and gRPC remote calls |

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
├── cli/               # CLI commands (create/run/plugin/config)
├── ovenware/          # Broker (message queue)
├── resource/          # YAML/JSON/XML config loaders
└── tool/              # Utilities
```

## TODO

### Core / IoC

- [x] Database migration support
- [x] Configuration hot-reload
- [x] Pagination `Page` object abstraction
- [x] OpenTelemetry / metrics integration
- [x] Graceful shutdown with signal handling
- [x] WebSocket support
- [x] Rate limiting middleware
- [x] API documentation auto-generation
- [x] More database dialects (SQLite/PG/MySQL type mapping)
- [x] Connection pool health check and auto-reconnect
- [x] JWT authentication support
- [x] Scheduled tasks (cron-like)
- [x] CLI interactive code (REPL)
- [x] Bean lifecycle callbacks — `on_init`(@PostConstruct), `on_destroy`(@PreDestroy)
- [x] Lazy initialization — `@Lazy` for deferred bean creation
- [x] Dependency resolution — `@DependsOn` topological sort, `@Import` auto-register
- [x] Async lifecycle — all lifecycle methods support `async def`
- [x] Zero import — all decorators/services auto-injected into builtins
- [x] Circular dependency detection — topological sort with cycle reporting
- [x] Integration tests — 42 tests covering multi-layer deps, diamond, edge cases
- [ ] Auto-configuration — auto-detect dependencies and configure defaults
- [ ] Profiles — environment-specific config (dev / test / prod)
- [ ] Conditional beans — `@ConditionalOnProperty`, `@ConditionalOnClass`
- [ ] Event system — `@EventListener`, application events (ContextRefreshed, etc.)
- [ ] Property binding — auto-map YAML/ENV to dataclass (`@ConfigurationProperties`)

### Web / REST

- [ ] CORS configuration — global and per-route CORS policy
- [ ] API versioning — `/api/v1/users`, `/api/v2/users`
- [ ] Exception handler — `@ExceptionHandler`, global error response
- [ ] Request logging middleware — auto-log method, path, status, duration
- [ ] Response compression — gzip/brotli middleware
- [ ] File upload — `@multipart`, multipart/form-data handling
- [ ] Server-Sent Events — `@sse_controller` for real-time push
- [ ] Request body validation — Pydantic-style `@Valid` on request models
- [ ] Content negotiation — JSON / XML response based on Accept header
- [ ] Async route handler — auto-detect async vs sync functions
- [ ] Static file serving — built-in static directory mount
- [ ] Request ID — auto-generate and propagate `X-Request-Id`

### Security

- [x] OAuth2 support — OAuth2 client and resource server
- [x] API key authentication — `@api_key_required` header-based auth
- [x] Password hashing — bcrypt/argon2 integration
- [x] CSRF protection — token-based CSRF for form submissions
- [x] Security headers — auto-add HSTS, X-Frame-Options, CSP
- [x] IP whitelist/blacklist — middleware-based IP filtering
- [x] Session management — server-side session with Redis/memory store

### Data / ORM

- [ ] Transaction propagation — REQUIRED, REQUIRES_NEW, NESTED
- [ ] Soft delete — `@SoftDelete`, `deleted_at` column support
- [ ] Auto timestamps — `created_at`, `updated_at` auto-fill
- [ ] Optimistic locking — version field for concurrent update safety
- [ ] Multi-datasource — connect to multiple databases simultaneously
- [ ] Database seeding — auto-insert initial data on startup
- [ ] Query logging — SQL statement logging with execution time
- [ ] Raw SQL helper — `db.execute_raw(sql)` with safety checks
- [ ] Relation mapping — one-to-many, many-to-many lazy/eager loading

### AOP / Middleware

- [ ] AOP (Aspect-Oriented Programming) — `@Before`, `@After`, `@Around` pointcuts
- [ ] Retry mechanism — `@Retry(max=3, delay=1)` for flaky operations
- [ ] Circuit breaker — `@CircuitBreaker` for fault tolerance
- [ ] Cache abstraction — `@Cacheable`, `@CacheEvict` (multi-backend: memory/Redis)
- [ ] Async execution — `@Async` for non-blocking background tasks
- [ ] Method timer — `@Timed` for method execution metrics
- [ ] Locking — `@DistributedLock` for concurrent access control

### Observability

- [ ] Structured logging — JSON log output with correlation ID
- [ ] Health indicators — custom health checks (DB, Redis, external API)
- [ ] Distributed tracing — OpenTelemetry trace context propagation
- [ ] Log levels API — runtime log level change via REST endpoint

### Plugin System

- [x] XML-based plugin declaration — `<dependencies>` in pancake.xml
- [x] Auto pip install — import-first, pip-fallback on ImportError
- [x] CLI management — `pancake plugin list/add/remove/clear`
- [x] CLI modularization — split monolithic cli.py into cli/ package
- [ ] Plugin marketplace — central registry for discovering plugins
- [ ] Plugin version constraints — `<version>` tag with semver matching
- [ ] Plugin hooks — `on_install`, `on_uninstall`, `on_upgrade` lifecycle

### DevOps / CLI

- [x] CLI modularization — split into cli/ package (project/config/plugin/misc)
- [ ] Project scaffolding — `pancake create` with templates (API / Fullstack / Microservice)
- [ ] Code generation — auto-generate Mapper/Controller from table schema
- [ ] DevTools — auto-restart on code change (watchdog)
- [ ] Docker support — auto-generate Dockerfile and docker-compose.yml
- [ ] Config validation — startup validation of required config keys
- [ ] Dry run — `pancake check` with full dependency and config validation

### Performance

- [ ] C extension — convert hot-path modules (sql_parser, wrapper, jwt) to C for speed

## Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## License

MIT
