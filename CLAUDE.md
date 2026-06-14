# CLAUDE.md

> Pancake Framework — 装饰器驱动的 Python 框架，集成 IoC、MyBatis Plus ORM 和 AI 工作流。

## 项目概述

Pancake 是一个全栈 Python 框架，核心理念是"零 import"——通过 `embed.py` 自动将所有装饰器、类和服务注入 `builtins`，用户代码无需显式 import 即可使用框架功能。

## 技术栈

- Python 3.10+
- Poetry 依赖管理
- databases + aiosqlite (异步 ORM)
- PyYAML + python-dotenv (配置)
- 可选: LangGraph、gRPC、Redis、aiohttp、OpenAI、Gemini、ChromaDB

## 项目结构

```
pancake/                    # 框架核心
├── __init__.py             # 入口引导: init() -> initialize 检查 -> 加载资源
├── run.py                  # 启动流水线: load_config -> load_ovenware -> load_dish -> build -> run_loop
├── ovenware/               # 插件模块 (自动发现加载)
│   ├── __init__.py         # InitAction 插件基类
│   └── broker.py           # 消息队列: @event_node / @on_event, SimpleBroker / RedisBroker
├── registry.py             # 统一注册表: 类、装饰器、实例、运行时数据
├── dough.py                # Bean 基类: Dough, DoughMeta, Scope
├── decorators/             # 装饰器模块
│   ├── scope.py            # @dough, @singleton, @prototype, @lazy
│   ├── inject.py           # @inject, @inject_name
│   ├── config.py           # @config, @depends_on, @import_class
│   ├── convert.py          # @service, @configuration, @function, @struct
│   ├── bean.py             # @maker, @maker_name, @no_maker
│   └── log.py              # @log 日志装饰器
├── exceptions.py           # 框架异常: PancakeError, ConfigError, PluginError 等
├── crash.py                # 异常处理: 完整异常写入 crash/ 目录
├── base/                   # 基类模块
│   ├── service.py          # Service 基类
│   ├── configuration.py    # Configuration 基类
│   ├── function.py         # Function 基类
│   └── struct.py           # Struct 基类
├── factory/                # 工厂模块
│   ├── dough_factory.py    # DoughFactory: Bean 工厂
│   └── package_manager.py  # PackageManager: 依赖检查
├── builder/                # 构建流水线
│   ├── build.py            # 实例化所有 Service，执行 BuildOrder
│   ├── load_dlc.py         # 自动发现 ovenware/ 下的插件，按 init_order 排序加载
│   └── load_src.py         # 扫描 src/ 下的 .py 文件，按 _load_priority 排序注册
├── settings.py             # 集中配置管理（路径、服务、数据库）
├── cli/                    # CLI 命令行工具 (pancake create/run/check/build)
│   ├── __init__.py         # main() argparse 入口
│   ├── project.py          # init/create/check/run/build 命令
│   ├── plugin.py           # plugin list/add/remove/clear 命令
│   ├── config.py           # config show 命令
│   ├── audit.py            # audit 命令
│   ├── misc.py             # version/cover/update/install 命令
│   └── utils.py            # get_version 工具函数
├── initialize/             # 环境检查
│   ├── check_env.py        # Poetry/依赖自动安装
│   ├── check_struct.py     # 项目结构完整性检查
│   └── print_ico.py        # 封面打印
├── resource/               # 配置加载器
│   ├── yml.py              # YAML 加载 + ${占位符} 解析 + 扁平化 key
│   ├── json.py             # JSON 加载
│   ├── config_watcher.py   # 配置热重载 (文件变更监听)
│   └── logging.py          # 日志配置
└── tool/
    └── progress_show.py    # 进度条工具

src/                        # 用户代码目录
├── mapper/                 # Mapper 层
├── resource/yaml/          # YAML 配置 (service.yaml, mybatis.yaml)
└── resource/db/            # SQLite 数据库

tests/                      # 测试
```

## 启动流程

1. `main.py` -> `pancake.run()`
2. `pancake/__init__.py` -> `init()`: 环境检查、结构检查、加载 resource 配置
3. `run.py` -> 按顺序执行:
   - `load_config`: 加载 YAML/JSON 配置到 settings
   - `load_ovenware`: 自动发现并加载 ovenware/ 插件 (按 `init_order` 排序)
   - `load_dish`: 扫描 src/ 下的用户代码，按 `_load_priority` 排序执行
   - `build`: 实例化 Bean，调用生命周期方法
   - `run_loop_methods`: 运行 loop_method

## 插件系统

### 加载优先级

- `init_order`: 控制 ovenware 插件初始化顺序 (值小先加载)
- `_load_priority`: 控制 src/ 用户代码加载顺序
- `build_order`: 控制 build 阶段执行顺序

### 自定义插件

在 `pancake/ovenware/` 下创建 `.py` 文件或子包，定义 `Main` 类 (含 `init_order`, `build()`, 可选 `check()`, `loop_method()`)。或通过 `EXTERNAL_PLUGIN_DIRS` 环境变量加载外部插件。

禁用内置插件: 在任意 YAML 中配置 `framework.disable_dlc: [plugin_name]`

## 核心用法

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

### 日志 @log

```python
@log
@service
class MyService:
    async def on_init(self):
        self.logger.info("服务启动")
```

logger 名称为 `{module}.{qualname}`，所有实例共享同一个 logger。

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
- 装饰器命名: `snake_case` (如 `auto_inject`, `event_node`)
- 类命名: `PascalCase` (如 `BaseMapper`, `IoCContainer`)
- 所有 ovenware 插件的装饰器/类需注册到 `registry.flour` 以便 embed 自动注入

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

#### 分支策略

| 分支 | 用途 | 权限 |
|------|------|------|
| `main` | 稳定分支，**禁止直接提交** | 只能通过 PR 合并 |
| `dev` | 开发分支，日常开发基于此分支 | PR 合并 |
| `feat/xxx` | 功能分支，从 `dev` 创建 | 自由推送 |
| `fix/xxx` | 修复分支 | 自由推送 |

工作流程:
1. 从 `dev` 创建分支: `git checkout -b feat/your-feature dev`
2. 开发完成后推送: `git push origin feat/your-feature`
3. 在 GitHub 创建 Pull Request，目标分支为 `dev`
4. 等待 CI 通过 + Code Review
5. 合并后删除功能分支

**禁止直接向 `main` / `dev` 推送代码，必须通过 Pull Request 合并。**

#### Commit 消息规范

- 使用中文或英文均可，但要清晰描述改动内容
- 格式: `<类型>: <简要描述>`
- 类型: `feat` / `fix` / `refactor` / `docs` / `test` / `chore`
- 示例: `feat: 添加用户注册接口` / `fix: 修复 SQL 注入漏洞` / `docs: 更新 CLAUDE.md`

#### PR 规范

- 标题必须符合 Commit 格式: `<type>: <描述>`
- 说明改动的原因和背景
- 确保 CI 测试通过
- 一个 PR 只做一件事，保持范围小

#### 禁止事项

- 禁止直接向 `main` / `dev` 推送代码
- 禁止提交 `.env`、密钥、密码等敏感文件
- 禁止提交 `.venv/`、`__pycache__/`、`*.db` 等生成文件
- 禁止使用 `git add .` 或 `git add -A`，必须明确指定文件

### 多实例协作规范

当多个 Claude 实例同时在同一仓库工作时，必须遵守以下规则避免冲突:

**开始前:**
1. 先执行 `git pull --rebase` 拉取最新代码
2. 执行 `git status` 检查工作区状态，**不要修改已被其他实例改动的文件**
3. 如果有未提交的修改，先 commit 或 stash，不要直接覆盖

**工作中:**
1. **改完即 commit** — 每完成一个逻辑单元就立即 commit，不要积压大量修改
2. **只改自己的文件** — 严格限定在分配给你的文件范围内，不要碰其他文件
3. **避免全局替换** — `replace_all` 可能误改其他实例正在编辑的文件
4. **提交前再 pull** — commit 前执行 `git pull --rebase`，确保不会覆盖他人提交

**冲突处理:**
- 遇到 merge conflict 时，保留双方修改，手动合并后 commit
- 不要 `git reset --hard` 或 `git checkout --` 丢弃他人的修改
- 如果不确定某个文件是否被其他实例修改，用 `git diff` 检查后再决定

**推荐分工方式:**
- 不同实例负责不重叠的目录或文件
- 或使用不同分支: `git checkout -b feat/xxx`，各自开发后合并

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

## 全局注册表 (registry 模块)

| 注册表 | 用途 | 示例键 |
|--------|------|--------|
| `flour` | 装饰器 | `Mapper`, `inject`, `event_node` |
| `water` | 类 | `IoCContainer`, `Scope`, `DoughFactory` |
| `egg` | 方法/构建器 | `Builder`, `LoopMethod`, `BuildOrder` |
| `sugar` | 其他 | `container` |
| `_class_registry` | 注册的类 | `UserMapper`, `MyService` |
| `_instance_registry` | 实例化的对象 | `UserMapper`, `SimpleBroker` |
| `_decorator_registry` | 装饰器注册表 | `Mapper`, `inject` |
| `_runtime_registry` | 运行时数据 | `langgraph_app` |

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
