# Pancake Framework

> A decorator-driven Python web framework with IoC, MyBatis-style ORM, and AI workflow integration.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/pancake_framework?style=flat-square&color=blue)
![CI](https://img.shields.io/github/actions/workflow/status/Drayee/PancakeFramework/ci.yml?style=flat-square&label=CI)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-009688?style=flat-square&logo=fastapi&logoColor=white)

</div>

[中文文档](./README_CN.md)

## Features

- **Zero Import** — All decorators and services auto-injected into builtins
- **Decorator-Driven** — Register controllers, mappers, services with simple decorators
- **CLI Tool** — `pancake create/run/check/build/plugin/config/audit`
- **MyBatis Plus ORM** — Async ORM with CRUD, `@Select`/`@Insert`, dynamic SQL, chain queries
- **FastAPI Web** — Controllers, filter chain (Spring Security-style), auth, middleware, WebSocket
- **IoC Container** — Singleton, transient, scoped dependency injection
- **AI Module** — Unified LLM client (OpenAI/DeepSeek/Gemini/Ollama), memory, RAG
- **Redis Cache** — `@cached` with anti-penetration/avalanche/breakdown protection
- **Message Queue** — Event-driven with SimpleBroker and RedisBroker
- **Remote Calls** — HTTP and gRPC via `@remote_node`
- **Lifecycle** — Init/start/stop/error hooks for components
- **Plugin System** — Auto-discovery, init-order control, external plugin dirs

## Quick Start

```bash
pip install pancake_framework
pancake create myapp && cd myapp
pancake run
```

Server starts at `http://127.0.0.1:8080`. Health check at `/health`.

### Minimal Example

```python
# No imports needed — everything is in builtins

@get_controller("/hello")
def hello():
    return {"message": "Hello from Pancake!"}

@Mapper
class UserMapper(BaseMapper):
    _entity_class = User
    _table_name = "users"

    @Select("SELECT * FROM users WHERE name = #{name}")
    async def find_by_name(self, name: str) -> list[User]: ...
```

## Documentation

| Module | Description |
|--------|-------------|
| [CLI](docs/cli.md) | Command-line tools |
| [Web](docs/web.md) | Controllers, filter chain, auth, middleware, WebSocket |
| [MyBatis ORM](docs/mybatis.md) | Mappers, CRUD, chain queries, dynamic SQL |
| [AI](docs/ai.md) | LLM client, memory, RAG |
| [Redis](docs/redis.md) | Cache, data structures, distributed locks |
| [IoC & DI](docs/ioc.md) | IoC container, `@auto_inject`, `@inject` |
| [Config](docs/config.md) | YAML/XML/env configuration |
| [Plugins](docs/plugin.md) | Plugin system and built-in plugins |
| [Lifecycle](docs/lifecycle.md) | Component lifecycle hooks |
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
- [ ] Auto-configuration — auto-detect dependencies and configure defaults
- [ ] Profiles — environment-specific config (dev / test / prod)
- [ ] Conditional beans — `@ConditionalOnProperty`, `@ConditionalOnClass`
- [ ] Bean lifecycle callbacks — `@PostConstruct`, `@PreDestroy`
- [ ] Lazy initialization — `@Lazy` for deferred bean creation
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

- [ ] OAuth2 support — OAuth2 client and resource server
- [ ] API key authentication — `@api_key_required` header-based auth
- [ ] Password hashing — bcrypt/argon2 integration
- [ ] CSRF protection — token-based CSRF for form submissions
- [ ] Security headers — auto-add HSTS, X-Frame-Options, CSP
- [ ] IP whitelist/blacklist — middleware-based IP filtering
- [ ] Session management — server-side session with Redis/memory store

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

### DevOps / CLI

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
