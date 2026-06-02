# Pancake Framework

> A decorator-driven Python web framework with IoC, MyBatis-style ORM, and AI workflow integration.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/pancake_framework?style=flat-square&color=blue)
![CI](https://img.shields.io/github/actions/workflow/status/Drayee/PancakeFramework/ci.yml?style=flat-square&label=CI)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square)

</div>

[中文文档](./README_CN.md)

## Features

- **Zero Import** - All decorators and services auto-injected into builtins, no import needed
- **Decorator-Driven** - Register services, controllers, and mappers with simple decorators
- **CLI Tool** - `pancake create/run/check/build` commands for project management
- **Auto Dependency Injection** - `@auto_inject()` automatically resolves parameters from YAML/JSON config
- **IoC Container** - Singleton, transient, and scoped dependency management
- **MyBatis Plus ORM** - Async ORM with `BaseMapper` CRUD, `@Select`/`@Insert` SQL annotations, dynamic SQL, chain queries
- **Multi-Database** - SQLite / PostgreSQL / MySQL with auto-detection
- **FastAPI Web Server** - Built-in `@get_controller`/`@post_controller` and all HTTP methods
- **Auth & Authorization** - `@auth_required`, `@role_required`, pluggable auth handlers
- **Middleware & Validation** - `@middleware`, `@validate`, `@transaction` decorators
- **AI Module** - Unified LLM client (OpenAI/DeepSeek/Gemini/Ollama), short-term & long-term memory, RAG
- **LangGraph Integration** - AI workflow nodes, edges, and state graphs
- **Redis Cache** - `@cached` decorator with anti-penetration/avalanche/breakdown protection
- **Message Queue** - In-memory `SimpleBroker` and `RedisBroker` for event-driven architecture
- **Remote Calls** - `@remote_node` for HTTP and gRPC remote invocation
- **Lifecycle Management** - `Lifecycle` base class with init/start/stop/error hooks
- **CUI** - Click-based CLI command registration with `@cui_command`
- **GUI** - Flet (Flutter) based GUI page registration with `@gui_page`
- **Plugin System** - Auto-discovery with init-order control, external plugin dirs
- **Centralized Settings** - All paths and configs managed through `settings.py`
- **Database Migration** - Version-based schema migration with auto-detect changes
- **Database Dialects** - Automatic SQLite / PostgreSQL / MySQL type mapping and syntax
- **Connection Health** - Ping, auto-reconnect for database connections
- **Rate Limiting** - `@rate_limit(times, seconds)` per-IP sliding window
- **WebSocket** - `@websocket_controller` for real-time communication
- **Config Hot-reload** - File watcher for YAML/JSON config changes
- **Metrics** - `/metrics` endpoint with request count, latency, error rate
- **API Docs** - Auto-generated Swagger (`/docs`) and ReDoc (`/redoc`)

## Quick Start

### Install

```bash
pip install pancake_framework
```

### Create a Project

```bash
pancake create myapp
cd myapp
```

### Run

```bash
# Using CLI
pancake run

# Or using Python
python main.py
```

The server starts at `http://127.0.0.1:8080` by default. Health check at `/health`.

### CLI Commands

| Command | Description |
|---------|-------------|
| `pancake create <name>` | Create a new project with standard structure |
| `pancake run` | Run the project |
| `pancake check` | Check project structure and environment |
| `pancake build` | Package project as wheel |

## Usage

### Web Controller (no import needed)

```python
@get_controller("/hello")
def hello():
    return {"message": "Hello from Pancake!"}

@post_controller("/users")
async def create_user(name: str, age: int):
    return {"id": await UserMapper().insert(name=name, age=age)}
```

### Auth & Authorization

```python
@set_auth_handler
async def authenticate(request, token):
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

@get_controller("/profile")
@auth_required
async def get_profile(current_user):
    return {"user": current_user}

@delete_controller("/admin/users/{user_id}")
@role_required("admin")
async def delete_user(user_id: int):
    await UserMapper().delete_by_id(user_id)
```

### Middleware & Transaction

```python
@middleware(order=1)
async def log_request(request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} {time.time()-start:.3f}s")
    return response

@post_controller("/transfer")
@transaction
async def transfer(from_id: int, to_id: int, amount: float):
    # All DB operations in this function run in a single transaction
    ...
```

### MyBatis Plus ORM (no import needed)

```python
@Mapper
class UserMapper(BaseMapper):
    @dataclass
    class User:
        id: int = None
        name: str = None
        age: int = None

    _entity_class = User
    _table_name = "users"

    @Select("SELECT * FROM users WHERE name = #{name}")
    async def find_by_name(self, name: str) -> list[User]: ...
```

Built-in CRUD: `select_by_id`, `select_list`, `select_one`, `select_count`, `insert`, `insert_batch`, `update_by_id`, `delete_by_id`.

Chain queries:

```python
users = await mapper.select(qw().ge("age", 18).like("name", "%Ali%").order_by_desc("age").limit(50))
await mapper.update(uw().set("name", "Bob").eq("id", 1))
await mapper.delete(qw().lt("age", 18))
```

### AI Module (no import needed)

Configure `src/resource/yaml/ai.yaml`, then use directly:

```python
# Chat
response = await chat_model.chat([{"role": "user", "content": "Hello"}])

# Stream
async for chunk in chat_model.chat_stream([...]):
    print(chunk, end="")

# Short-term memory (session context)
await short_term_memory.add("session_001", "user", "My name is Alice")
messages = await short_term_memory.get_messages("session_001")

# Long-term memory (persistent)
await long_term_memory.remember("user_name", "Alice")
name = await long_term_memory.recall("user_name")

# RAG
await rag.add_document("Pancake is a Python framework...")
answer = await rag.ask("What is Pancake?")
```

Supported providers: OpenAI, DeepSeek, Gemini, Ollama, GLM, Moonshot, Qwen, vLLM.

### Redis Cache

```python
@cached(ttl=300)
async def get_user(user_id: int):
    return await db.query(user_id)

# CacheGuard with anti-penetration/avalanche/breakdown
guard = CacheGuard(redis_client)
user = await guard.get_or_load("user:123", lambda: db.query(123), ttl=600, jitter=60)
```

### Event-Driven Messaging

```python
@event_node(name="order_created", event="order.created")
async def create_order(item: str, qty: int):
    return {"item": item, "qty": qty, "status": "created"}

@on_event("order.created")
async def notify_inventory(message):
    print(f"Order received: {message}")
```

### Lifecycle Hooks

```python
class MyService(Lifecycle):
    async def on_init(self):
        self.cache = {}

    async def on_start(self):
        await self.load_data()

    async def on_stop(self):
        await self.cleanup()
```

### CUI (CLI Commands)

```python
@cui_command("greet", help="Say hello")
@cui_option("--name", "-n", default="World", help="Name")
def greet(name: str):
    click.echo(f"Hello, {name}!")
```

### GUI (Flet/Flutter)

```python
@gui_page("/", title="Home")
def home(page: ft.Page):
    page.add(ft.Text("Welcome to Pancake GUI"))
```

## Optional Dependencies

```bash
pip install pancake_framework[ai]          # AI module (OpenAI, Gemini, etc.)
pip install pancake_framework[langgraph]   # LangGraph AI workflow
pip install pancake_framework[redis]       # Redis cache and message queue
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

## Running Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## License

MIT
