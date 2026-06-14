# 2. Core Concepts

[← Previous](01-quickstart.md) | [Next →](03-ioc.md)

---

## Dough — Bean Base Class

`Dough` is the base class for all framework types, similar to Spring's `Object`. All custom Beans should extend `Dough` or its subclasses.

```python
class MyBean(Dough):
    async def on_init(self):
        # Called after initialization (@PostConstruct)
        pass

    async def on_start(self):
        # Called when ready
        pass

    async def on_stop(self):
        # Called when stopping
        pass

    async def on_destroy(self):
        # Called before destruction (@PreDestroy)
        pass
```

## Lifecycle

```
__init__()  →  on_init()  →  on_start()  →  [running]  →  on_stop()  →  on_destroy()
   construct    @PostConstruct    ready                        stop         @PreDestroy
```

All lifecycle methods support both sync and async implementations. `DoughFactory` auto-detects and calls them correctly.

```python
# Sync
class SyncBean(Dough):
    def on_init(self):
        print("initialized")

# Async
class AsyncBean(Dough):
    async def on_init(self):
        await some_async_operation()
```

## Scopes

| Scope | Decorator | Description |
|-------|-----------|-------------|
| Singleton | `@singleton` | One instance per factory (default) |
| Prototype | `@prototype` | New instance every resolve |
| Lazy | `@lazy` | Created on first access |

```python
@singleton
class MyService(Service):
    pass

@prototype
class MyPrototype(Service):
    pass

@lazy
class MyLazy(Service):
    pass
```

## Base Classes

| Base | Purpose | Example |
|------|---------|---------|
| `Service` | Service, method collection | `UserService`, `OrderService` |
| `Configuration` | Config, method returns auto-register as Beans | `AppConfig`, `DatabaseConfig` |
| `Struct` | Data structure (dataclass) | `User`, `OrderForm` |
| `Function` | Function wrapper | `FormatDate`, `ValidateEmail` |

### Service

```python
class UserService(Service):
    async def find_user(self, user_id: int):
        return {"id": user_id, "name": "Alice"}
```

### Configuration

```python
@configuration
class AppConfig(Configuration):
    def cache_manager(self):
        """Return value auto-registers as Bean"""
        return CacheManager()

    @no_maker
    def helper(self):
        return "not a bean"
```

### Struct

```python
@struct
class UserForm:
    name: str = None
    email: str = None
    age: int = None

form = UserForm(name="Alice", email="alice@example.com", age=25)
```

### Function

```python
@function
def format_date(date_str: str) -> str:
    from datetime import datetime
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")

result = format_date("2024-01-15")  # "15/01/2024"
```

## Logging — @log

The `@log` decorator automatically injects a `logger` instance into a class (similar to Lombok's `@Slf4j`), eliminating the need to write `logging.getLogger(...)` everywhere.

```python
@log
@service
class UserService:
    async def on_init(self):
        self.logger.info("UserService started")

    async def find_user(self, user_id: int):
        self.logger.debug(f"Finding user: {user_id}")
        try:
            user = await self._query(user_id)
            self.logger.info(f"Found user: {user_id}")
            return user
        except Exception as e:
            self.logger.error(f"Query failed: {e}", exc_info=True)
            raise
```

The logger name format is `{module}.{class}`, e.g., `src.service.user.UserService`. All instances share the same logger.

---

[← Previous](01-quickstart.md) | [Next →](03-ioc.md)
