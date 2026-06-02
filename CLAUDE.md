# CLAUDE.md

> Pancake Framework — 装饰器驱动的 Python Web 框架，集成 IoC、MyBatis Plus ORM 和 AI 工作流。

## 项目概述

Pancake 是一个全栈 Python 框架，核心理念是"零 import"——通过 `embed.py` 自动将所有装饰器、类和服务注入 `builtins`，用户代码无需显式 import 即可使用框架功能。

## 技术栈

- Python 3.13+
- Poetry 依赖管理
- FastAPI + Uvicorn (Web 服务)
- databases + aiosqlite (异步 ORM)
- PyYAML + python-dotenv (配置)
- 可选: LangGraph、gRPC、Redis、aiohttp、OpenAI、Gemini、ChromaDB

## 项目结构

```
pancake/                    # 框架核心
├── __init__.py             # 入口引导: init() -> initialize 检查 -> 加载资源
├── run.py                  # 启动流水线: load_config -> load_ovenware -> oven_init -> load_dish -> build -> run_loop
├── oven/                   # 全局注册表
│   ├── pancake.py          # pancake_yaml/json/dough/pie/other — 存储配置、类、实例
│   ├── muffin.py           # muffin_flour/water/egg/suger — 存储装饰器、类、方法
│   └── default.py          # 默认初始化: 加载 YAML/JSON，初始化 dough/pie/other
├── ovenware/               # 插件模块 (自动发现加载)
│   ├── base.py             # @Service 装饰器
│   ├── inject.py           # 统一依赖注入: IoCContainer + @auto_inject + @inject
│   ├── web.py              # FastAPI: @get_controller / @post_controller
│   ├── embed.py            # builtins 注入 (init_order=-10, 最先加载)
│   ├── broker.py           # 消息队列: @event_node / @on_event, SimpleBroker / RedisBroker
│   ├── lifecycle.py        # 生命周期: Lifecycle 基类, @lifecycle_node, LifecycleManager
│   ├── remote.py           # 远程调用: @remote_node, HttpRemote / GrpcRemote
│   ├── redis_cache.py      # Redis 缓存: @cached, CacheGuard（防穿透/雪崩/击穿）
│   ├── ai_model.py         # AI 模块: ChatModel, ShortTermMemory, LongTermMemory, RAG
│   ├── external_plugin.py  # 外部插件加载 (EXTERNAL_PLUGIN_DIRS 环境变量)
│   ├── mybatis/            # MyBatis Plus ORM
│   │   ├── mapper.py       # @Mapper, BaseMapper, @Select/@Insert/@Update/@Delete
│   │   ├── wrapper.py      # QueryWrapper / UpdateWrapper 链式查询
│   │   ├── sql_parser.py   # #{param} 绑定 + 动态 SQL (<if>/<where>/<set>/<foreach>/<choose>)
│   │   ├── connection.py   # 异步数据库连接管理 (databases 库)
│   │   └── config.py       # mybatis 配置加载
│   └── langgraph/          # AI 工作流核心
│       └── core.py         # @langgraph_node / @langgraph_edge
├── builder/                # 构建流水线
│   ├── build.py            # 实例化所有 Service，执行 BuildOrder
│   ├── load_dlc.py         # 自动发现 ovenware/ 下的插件，按 init_order 排序加载
│   └── load_src.py         # 扫描 src/ 下的 .py 文件，按 _load_priority 排序注册
├── settings.py             # 集中配置管理（路径、服务、数据库）
├── cli.py                  # CLI 命令行工具 (pancake create/run/check/build)
├── initialize/             # 环境检查
│   ├── check_env.py        # Poetry/依赖自动安装
│   ├── check_struct.py     # 项目结构完整性检查
│   └── check_dlc.py        # 插件检查
├── resource/               # 配置加载器
│   ├── yml.py              # YAML 加载 + ${占位符} 解析 + 扁平化 key
│   ├── json.py             # JSON 加载
│   ├── config.py           # dotenv 加载
│   └── logging.py          # 日志配置
└── tool/
    └── progress_show.py    # 进度条工具

src/                        # 用户代码目录
├── controller.py           # Web 控制器示例
├── mapper/                 # Mapper 层
├── resource/yaml/          # YAML 配置 (service.yaml, mybatis.yaml)
└── resource/db/            # SQLite 数据库

tests/                      # 测试
```

## 启动流程

1. `main.py` -> `pancake.run()`
2. `pancake/__init__.py` -> `init()`: 环境检查、结构检查、加载 resource 配置
3. `run.py` -> 按顺序执行:
   - `load_config`: 加载 YAML/JSON 配置到 `oven.pancake_yaml/json`
   - `load_ovenware`: 自动发现并加载 ovenware/ 插件 (按 `init_order` 排序)
   - `oven_init`: 默认后处理
   - `load_dish`: 扫描 src/ 下的用户代码，按 `_load_priority` 排序执行
   - `build`: 实例化 Service，执行 Builder
   - `run_loop_methods`: 运行 loop_method (如 uvicorn Web 服务器)

## 插件系统

### 加载优先级

- `init_order`: 控制 ovenware 插件初始化顺序 (值小先加载, embed=-10, mybatis=1, web=50)
- `_load_priority`: 控制 src/ 用户代码加载顺序 (Mapper=10, controller 默认=50)
- `build_order`: 控制 build 阶段执行顺序

### 自定义插件

在 `pancake/ovenware/` 下创建 `.py` 文件或子包，定义 `Main` 类 (含 `init_order`, `build()`, 可选 `check()`, `loop_method()`)。或通过 `EXTERNAL_PLUGIN_DIRS` 环境变量加载外部插件。

禁用内置插件: 在任意 YAML 中配置 `framework.disable_dlc: [langgraph, external_plugin]`

## 核心用法

### Web 控制器 (无需 import)

```python
@get_controller("/hello")
def hello():
    return {"message": "Hello"}

@post_controller("/users")
async def create_user(name: str, age: int):
    return {"id": await UserMapper().insert(name=name, age=age)}
```

### MyBatis Plus Mapper (无需 import)

```python
@Mapper
class UserMapper(BaseMapper):
    @dataclass
    class User:
        id: int = None
        name: str = None

    _entity_class = User
    _table_name = "users"

    @Select("SELECT * FROM users WHERE name = #{name}")
    async def find_by_name(self, name: str) -> list[User]: ...
```

链式查询: `qw().eq("name", "Alice").ge("age", 18).order_by_desc("age").limit(50)`

### IoC 容器

```python
container.register(UserService, UserService, Scope.SINGLETON)
service = container.resolve(UserService)
```

### 自动注入

```python
@auto_inject()
def get_config(service_title: str, service_port: int):
    return {"title": service_title, "port": service_port}
```

### AI 模块 (无需 import)

配置 `src/resource/yaml/ai.yaml` 后直接使用：

```python
# 对话
response = await chat_model.chat([{"role": "user", "content": "你好"}])

# 指定模型
response = await chat_model.chat([...], model="gemini")

# 流式输出
async for chunk in chat_model.chat_stream([...]):
    print(chunk, end="")

# 短期记忆（对话上下文）
short_term_memory.add("user", "我叫小明")
short_term_memory.add("assistant", "你好小明！")
messages = short_term_memory.get_messages()

# 长期记忆（持久化存储）
await long_term_memory.remember("user_name", "小明")
name = await long_term_memory.recall("user_name")

# RAG 问答
await rag.add_document("Pancake 是一个 Python 框架...")
answer = await rag.ask("什么是 Pancake？")
```

支持的模型提供商：OpenAI、DeepSeek、Gemini、Ollama、智谱 GLM、Moonshot、Qwen、vLLM

## 开发规范

### 代码风格

- 中文注释和日志信息
- 使用 `logging` 模块，不要用 `print`
- 装饰器命名: `snake_case` (如 `get_controller`, `auto_inject`)
- 类命名: `PascalCase` (如 `BaseMapper`, `IoCContainer`)
- 所有 ovenware 插件的装饰器/类需注册到 `oven.muffin_flour` 以便 embed 自动注入

### 安全

- SQL 标识符 (表名、列名) 必须通过 `_validate_identifier()` 校验，防注入
- 使用参数化查询 (`#{param}` -> `:param`)，禁止字符串拼接 SQL
- `QueryWrapper.last()` 有注入风险，慎用

### Git 规范

**每次修改代码后必须提交 git commit。** 无论是新增功能、修复 bug、修改配置还是重构代码，完成后都应立即 commit。

```bash
# 完成修改后必须执行
git add <修改的文件>
git commit -m "<描述>"
```

Commit 消息规范:
- 使用中文或英文均可，但要清晰描述改动内容
- 格式: `<类型>: <简要描述>`
- 类型: `feat` / `fix` / `refactor` / `docs` / `test` / `chore`
- 示例: `feat: 添加用户注册接口` / `fix: 修复 SQL 注入漏洞` / `docs: 更新 CLAUDE.md`

禁止事项:
- 禁止提交 `.env`、密钥、密码等敏感文件
- 禁止提交 `.venv/`、`__pycache__/`、`*.db` 等生成文件
- 禁止使用 `git add .` 或 `git add -A`，必须明确指定文件

### 测试

```bash
python -m pytest tests/ -v
```

测试文件在 `tests/` 下，需手动 `sys.path.insert` 指向 `pancake/` 目录。

### 运行

```bash
poetry run python main.py
# 或
python main.py
```

服务默认监听 `http://127.0.0.1:8080`

## 全局注册表 (oven 模块)

| 注册表 | 用途 | 示例键 |
|--------|------|--------|
| `pancake_yaml` | YAML 配置 (扁平化) | `service.title`, `mybatis.database.url` |
| `pancake_json` | JSON 配置 | - |
| `pancake_dough` | 注册的类 | `Service`, `Mapper`, `langgraph_node` |
| `pancake_pie` | 实例化的对象 | `Service.UserMapper` |
| `pancake_other` | 运行时数据 | `path`, `langgraph_app` |
| `muffin_flour` | 装饰器 | `Mapper`, `get_controller`, `inject` |
| `muffin_water` | 类 | `IoCContainer`, `Lifecycle`, `Scope` |
| `muffin_egg` | 方法/构建器 | `Builder`, `LoopMethod`, `BuildOrder` |
| `muffin_suger` | 其他 | `container` |

## 配置项

| 键 | 说明 | 默认值 |
|----|------|--------|
| `service.title` | 应用名称 | - |
| `service.version` | 应用版本 | - |
| `service.host` | 绑定地址 | `127.0.0.1` |
| `service.port` | 绑定端口 | `8080` |
| `mybatis.database.url` | 数据库 URL | `sqlite:///resource/db/app.db` |
| `mybatis.database.min_size` | 连接池最小 | `1` |
| `mybatis.database.max_size` | 连接池最大 | `5` |
| `framework.disable_dlc` | 禁用插件列表 | `[]` |
