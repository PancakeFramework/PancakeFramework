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
- **插件系统** — XML 声明式管理，自动 pip 安装，`pancake plugin` 命令行

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
├── cli/               # CLI 命令（create/run/plugin/config）
├── ovenware/          # Broker 消息队列
├── resource/          # YAML/JSON/XML 配置加载器
└── tool/              # 工具类
```

## TODO

### 核心 / IoC

- [x] 数据库迁移支持
- [x] 配置热重载
- [x] 分页 `Page` 对象抽象
- [x] OpenTelemetry / 指标集成
- [x] 优雅关闭（信号处理）
- [x] WebSocket 支持
- [x] 限流中间件
- [x] API 文档自动生成
- [x] 多数据库方言（SQLite/PG/MySQL 类型映射）
- [x] 连接池健康检查和自动重连
- [x] JWT 认证支持
- [x] 定时任务（cron）
- [x] CLI 交互式代码（REPL）
- [x] Bean 生命周期回调 — `on_init`(@PostConstruct)、`on_destroy`(@PreDestroy)
- [x] 懒加载 — `@Lazy` 延迟 Bean 创建
- [x] 依赖解析 — `@DependsOn` 拓扑排序、`@Import` 自动注册
- [x] 异步生命周期 — 所有生命周期方法支持 `async def`
- [x] 零 import — 所有装饰器/服务自动注入 builtins
- [x] 循环依赖检测 — 拓扑排序检测并报告循环
- [x] 集成测试 — 42 个测试覆盖多层依赖、菱形依赖、边界场景
- [ ] 自动配置 — 自动检测依赖并配置默认值
- [ ] Profiles — 环境特定配置（dev / test / prod）
- [ ] 条件 Bean — `@ConditionalOnProperty`、`@ConditionalOnClass`
- [ ] 事件系统 — `@EventListener`、应用事件（ContextRefreshed 等）
- [ ] 属性绑定 — YAML/ENV 自动映射到 dataclass（`@ConfigurationProperties`）

### Web / REST

- [ ] CORS 配置 — 全局和按路由 CORS 策略
- [ ] API 版本控制 — `/api/v1/users`、`/api/v2/users`
- [ ] 异常处理器 — `@ExceptionHandler`、全局错误响应
- [ ] 请求日志中间件 — 自动记录 method、path、status、duration
- [ ] 响应压缩 — gzip/brotli 中间件
- [ ] 文件上传 — `@multipart`、multipart/form-data 处理
- [ ] Server-Sent Events — `@sse_controller` 实时推送
- [ ] 请求体验证 — Pydantic 风格 `@Valid` 请求模型
- [ ] 内容协商 — 根据 Accept 头返回 JSON / XML
- [ ] 异步路由 — 自动检测 async vs sync 函数
- [ ] 静态文件服务 — 内置静态目录挂载
- [ ] 请求 ID — 自动生成和传播 `X-Request-Id`

### 安全

- [x] OAuth2 支持 — OAuth2 客户端和资源服务器
- [x] API Key 认证 — `@api_key_required` 基于头部的认证
- [x] 密码哈希 — bcrypt/argon2 集成
- [x] CSRF 保护 — 基于 Token 的 CSRF 表单提交保护
- [x] 安全头部 — 自动添加 HSTS、X-Frame-Options、CSP
- [x] IP 白名单/黑名单 — 基于中间件的 IP 过滤
- [x] 会话管理 — 服务端会话，支持 Redis/内存存储

### 数据 / ORM

- [ ] 事务传播 — REQUIRED、REQUIRES_NEW、NESTED
- [ ] 软删除 — `@SoftDelete`、`deleted_at` 列支持
- [ ] 自动时间戳 — `created_at`、`updated_at` 自动填充
- [ ] 乐观锁 — version 字段并发更新安全
- [ ] 多数据源 — 同时连接多个数据库
- [ ] 数据库种子 — 启动时自动插入初始数据
- [ ] 查询日志 — SQL 语句日志及执行时间
- [ ] 原始 SQL 辅助 — `db.execute_raw(sql)` 带安全检查
- [ ] 关系映射 — 一对多、多对多懒加载/急加载

### AOP / 中间件

- [ ] AOP（面向切面编程）— `@Before`、`@After`、`@Around` 切点
- [ ] 重试机制 — `@Retry(max=3, delay=1)` 不稳定操作
- [ ] 熔断器 — `@CircuitBreaker` 容错
- [ ] 缓存抽象 — `@Cacheable`、`@CacheEvict`（多后端：内存/Redis）
- [ ] 异步执行 — `@Async` 非阻塞后台任务
- [ ] 方法计时 — `@Timed` 方法执行指标
- [ ] 分布式锁 — `@DistributedLock` 并发访问控制

### 可观测性

- [ ] 结构化日志 — JSON 日志输出带关联 ID
- [ ] 健康指标 — 自定义健康检查（DB、Redis、外部 API）
- [ ] 分布式追踪 — OpenTelemetry 追踪上下文传播
- [ ] 日志级别 API — 运行时通过 REST 端点修改日志级别

### 插件系统

- [x] XML 声明式插件 — pancake.xml `<dependencies>` 管理
- [x] 自动 pip 安装 — import 优先，ImportError 时自动 pip install
- [x] CLI 管理 — `pancake plugin list/add/remove/clear`
- [x] CLI 模块化 — 拆分为 cli/ 包（project/config/plugin/misc）
- [ ] 插件市场 — 集中注册表发现插件
- [ ] 插件版本约束 — `<version>` 标签支持 semver 匹配
- [ ] 插件钩子 — `on_install`、`on_uninstall`、`on_upgrade` 生命周期

### DevOps / CLI

- [x] CLI 模块化 — 拆分为 cli/ 包（project/config/plugin/misc）
- [ ] 项目脚手架 — `pancake create` 模板（API / 全栈 / 微服务）
- [ ] 代码生成 — 从表结构自动生成 Mapper/Controller
- [ ] DevTools — 代码变更自动重启（watchdog）
- [ ] Docker 支持 — 自动生成 Dockerfile 和 docker-compose.yml
- [ ] 配置验证 — 启动时验证必需配置项
- [ ] 试运行 — `pancake check` 完整依赖和配置验证

### 性能

- [ ] C 扩展 — 将热路径模块（sql_parser、wrapper、jwt）转为 C 加速

## 测试

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## 开源协议

MIT
