"""
AI 模块 — 统一 LLM 调用 + 记忆管理 + RAG

提供可直接 inject 的 AI 组件：
  chat_model           — ChatModel 实例（全局单例）
  short_term_memory    — ShortTermMemory 实例（会话记忆）
  long_term_memory     — LongTermMemory 实例（长期记忆）
  rag                  — RAG 实例（检索增强生成）

记忆和 RAG 实现在 ai_memory.py 中，本文件负责：
  1. ChatModel（LLM 调用）
  2. 全局实例管理
  3. 插件 Main 类（配置读取 + 初始化）

配置项（YAML）：
  ai.default_model: deepseek
  ai.providers.<name>.type: openai | google | ollama
  ai.memory.short_term.backend: memory | redis | mybatis
  ai.memory.long_term.backend: memory | redis | mybatis
  ai.rag.backend: pgvector | redis | mongodb

可选依赖：pip install pancake[ai]
"""

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator

from pancake import oven
from pancake.ovenware import check_dependencies
from .ai_memory import (
    ShortTermMemory, LongTermMemory, RAG,
    InMemoryBackend, RedisBackend, MyBatisBackend,
    PgVectorBackend, RedisVectorBackend, MongoVectorBackend,
    _create_memory_backend, _create_vector_backend,
)

logger = logging.getLogger(__name__)


# ============================================================
#  默认配置
# ============================================================

_DEFAULT_CONFIG = {
    "default_model": "deepseek",
    "providers": {
        "deepseek": {
            "type": "openai",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "model": "deepseek-chat",
            "max_tokens": 4096,
            "temperature": 0.7,
            "timeout": 60,
            "retry": 3,
        }
    },
    "memory": {
        "short_term": {
            "backend": "memory",
            "table_name": "ai_short_term",
            "ttl": 86400,
            "max_messages": 20,
        },
        "long_term": {
            "backend": "memory",
            "table_name": "ai_long_term",
            "ttl": 0,
        },
    },
    "rag": {
        "backend": "pgvector",
        "table_name": "ai_rag_docs",
        "embedding_provider": None,
        "embedding_model": "text-embedding-3-small",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 5,
        "dimension": 1536,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并字典，override 覆盖 base"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _resolve_env(value: str) -> str:
    """解析 ${ENV_VAR} 占位符"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_key = value[2:-1]
        return os.environ.get(env_key, "")
    return value


def _resolve_env_recursive(obj):
    """递归解析配置中的 ${ENV_VAR} 占位符"""
    if isinstance(obj, dict):
        return {k: _resolve_env_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_recursive(i) for i in obj]
    if isinstance(obj, str):
        return _resolve_env(obj)
    return obj


# ============================================================
#  Provider 基类和实现
# ============================================================

class BaseProvider:
    """
    LLM Provider 基类

    用户可继承重写：
        class MyProvider(OpenAIProvider):
            async def chat(self, messages, **kwargs):
                return await super().chat(messages, **kwargs)
    """

    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 60)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError

    async def embed(self, text: str, **kwargs) -> list[float]:
        raise NotImplementedError


class OpenAIProvider(BaseProvider):
    """OpenAI 兼容 API（DeepSeek/智谱/Moonshot/Qwen/vLLM）"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.api_key = config.get("api_key", "")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "none",
                timeout=self.timeout,
            )
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        for attempt in range(self.config.get("retry", 3)):
            try:
                resp = await client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            except Exception as e:
                if attempt == self.config.get("retry", 3) - 1:
                    raise
                logger.warning(f"LLM 调用失败，重试 {attempt + 1}: {e}")
                await asyncio.sleep(1)

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        client = await self._get_client()
        stream = await client.chat.completions.create(
            model=kwargs.get("model", self.model), messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed(self, text: str, **kwargs) -> list[float]:
        client = await self._get_client()
        model = kwargs.get("model", self.config.get("embedding_model", "text-embedding-3-small"))
        resp = await client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding


class GoogleProvider(BaseProvider):
    """Google Gemini"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        client = await self._get_client()
        system_instruction, contents = self._convert_messages(messages)
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=kwargs.get("model", self.model), contents=contents,
            config={"system_instruction": system_instruction} if system_instruction else None,
        )
        return resp.text

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        client = await self._get_client()
        system_instruction, contents = self._convert_messages(messages)
        stream = await asyncio.to_thread(
            client.models.generate_content_stream,
            model=kwargs.get("model", self.model), contents=contents,
            config={"system_instruction": system_instruction} if system_instruction else None,
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    async def embed(self, text: str, **kwargs) -> list[float]:
        client = await self._get_client()
        resp = await asyncio.to_thread(
            client.models.embed_content,
            model=kwargs.get("model", "text-embedding-004"), contents=text,
        )
        return resp.embeddings[0].values

    def _convert_messages(self, messages: list[dict]) -> tuple[str | None, list]:
        """将 OpenAI 格式消息转为 Gemini 格式

        Returns:
            (system_instruction, contents) — system 消息单独提取
        """
        system_parts = []
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system_parts.append(msg["content"])
            elif role == "user":
                contents.append({"role": "user", "parts": [msg["content"]]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [msg["content"]]})
        system_instruction = "\n".join(system_parts) if system_parts else None
        return system_instruction, contents


class OllamaProvider(BaseProvider):
    """Ollama 本地模型"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")

    async def chat(self, messages: list[dict], **kwargs) -> str:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={"model": kwargs.get("model", self.model), "messages": messages, "stream": False},
            ) as resp:
                data = await resp.json()
                return data["message"]["content"]

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={"model": kwargs.get("model", self.model), "messages": messages, "stream": True},
            ) as resp:
                async for line in resp.content:
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]

    async def embed(self, text: str, **kwargs) -> list[float]:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/embed",
                json={"model": kwargs.get("model", self.model), "input": text},
            ) as resp:
                data = await resp.json()
                return data["embeddings"][0]


_PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "google": GoogleProvider,
    "ollama": OllamaProvider,
}


def register_provider(name: str, provider_class: type[BaseProvider]):
    """注册自定义 Provider"""
    _PROVIDER_REGISTRY[name] = provider_class


# ============================================================
#  ChatModel — 统一 LLM 客户端
# ============================================================

class ChatModel:
    """
    统一 LLM 调用接口

    使用方法：
        response = await chat_model.chat([{"role": "user", "content": "你好"}])
        response = await chat_model.chat([...], model="gemini")
        async for chunk in chat_model.chat_stream([...]):
            print(chunk, end="")
    """

    def __init__(self, config: dict):
        self._config = config
        self._default = config.get("default_model", "deepseek")
        self._providers: dict[str, BaseProvider] = {}

    def _get_or_create_provider(self, name: str) -> BaseProvider:
        if name not in self._providers:
            provider_config = self._config.get("providers", {}).get(name)
            if not provider_config:
                raise ValueError(f"未配置的模型提供商: {name}")
            provider_type = provider_config.get("type", "openai")
            provider_class = _PROVIDER_REGISTRY.get(provider_type)
            if not provider_class:
                raise ValueError(f"不支持的 provider 类型: {provider_type}")
            if provider_type != "ollama" and not provider_config.get("api_key"):
                raise ValueError(
                    f"AI Provider '{name}' 的 API Key 未配置，"
                    f"请在 ai.providers.{name}.api_key 或对应环境变量中设置"
                )
            self._providers[name] = provider_class(provider_config)
            logger.info(f"创建 LLM Provider: {name} ({provider_type})")
        return self._providers[name]

    def get_provider(self, name: str = None) -> BaseProvider:
        return self._get_or_create_provider(name or self._default)

    async def chat(self, messages: list[dict], model: str = None,
                   temperature: float = None, max_tokens: int = None) -> str:
        provider = self._get_or_create_provider(model or self._default)
        return await provider.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def chat_stream(self, messages: list[dict], model: str = None,
                          temperature: float = None, max_tokens: int = None) -> AsyncIterator[str]:
        provider = self._get_or_create_provider(model or self._default)
        async for chunk in provider.chat_stream(messages, temperature=temperature, max_tokens=max_tokens):
            yield chunk

    async def embed(self, text: str, model: str = None) -> list[float]:
        provider = self._get_or_create_provider(model or self._default)
        return await provider.embed(text)


# ============================================================
#  AI 管理器
# ============================================================


class AIManager:
    """
    AI 管理器 — 封装全局 AI 实例状态

    使用方法:
        manager = AIManager()
        # 由 Main.__init__ 初始化
        chat_model = manager.get_chat_model()
        manager.reset()
    """

    def __init__(self):
        self._chat_model: ChatModel | None = None
        self._short_term_memory: ShortTermMemory | None = None
        self._long_term_memory: LongTermMemory | None = None
        self._rag: RAG | None = None

    def get_chat_model(self) -> ChatModel | None:
        return self._chat_model

    def get_short_term_memory(self) -> ShortTermMemory | None:
        return self._short_term_memory

    def get_long_term_memory(self) -> LongTermMemory | None:
        return self._long_term_memory

    def get_rag(self) -> RAG | None:
        return self._rag

    def reset(self):
        """重置状态（用于测试）"""
        self._chat_model = None
        self._short_term_memory = None
        self._long_term_memory = None
        self._rag = None


# 向后兼容的模块级默认实例
_manager = AIManager()

get_chat_model = _manager.get_chat_model
get_short_term_memory = _manager.get_short_term_memory
get_long_term_memory = _manager.get_long_term_memory
get_rag = _manager.get_rag


def create_manager() -> AIManager:
    """创建新的独立管理器（用于测试）"""
    return AIManager()


# ============================================================
#  插件 Main 类
# ============================================================

class Main(InitAction):
    """AI 模块插件主类"""

    init_order = 4  # redis 之后，web 之前
    _dependencies = ["openai"]
    _extras = "ai"

    def __init__(self):
        user_config = self._build_config_from_flat_keys()
        config = _deep_merge(_DEFAULT_CONFIG, user_config)
        config = _resolve_env_recursive(config)

        # ChatModel
        _manager._chat_model = ChatModel(config)

        # ShortTermMemory
        st_config = config.get("memory", {}).get("short_term", {})
        st_backend = _create_memory_backend(st_config)
        _manager._short_term_memory = ShortTermMemory(st_backend, st_config)

        # LongTermMemory
        lt_config = config.get("memory", {}).get("long_term", {})
        lt_backend = _create_memory_backend(lt_config)
        _manager._long_term_memory = LongTermMemory(lt_backend, lt_config)

        # RAG
        rag_config = config.get("rag", {})
        try:
            rag_backend = _create_vector_backend(rag_config)
            _manager._rag = RAG(rag_backend, rag_config)
        except Exception as e:
            logger.warning(f"RAG 初始化失败: {e}")

        # 保存到 oven
        oven.pancake_other["chat_model"] = _manager._chat_model
        oven.pancake_other["short_term_memory"] = _manager._short_term_memory
        oven.pancake_other["long_term_memory"] = _manager._long_term_memory
        oven.pancake_other["rag"] = _manager._rag

    @staticmethod
    def _build_config_from_flat_keys() -> dict:
        result = {}
        for flat_key, value in oven.pancake_yaml.items():
            if not flat_key.startswith("ai."):
                continue
            parts = flat_key.split(".")
            current = result
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value
        return result.get("ai", {})

    @staticmethod
    def check():
        check_dependencies(Main._dependencies, Main._extras)

    def build(self):
        logger.info("AI 模块构建完成")

    def loop_method(self):
        cm = _manager.get_chat_model()
        if cm:
            logger.info(f"AI 模块就绪，默认模型: {cm._default}")


# ============================================================
#  注册到 oven
# ============================================================

oven.muffin_flour["ChatModel"] = ChatModel
oven.muffin_flour["ShortTermMemory"] = ShortTermMemory
oven.muffin_flour["LongTermMemory"] = LongTermMemory
oven.muffin_flour["RAG"] = RAG
oven.muffin_flour["register_provider"] = register_provider

oven.muffin_sugar["chat_model"] = get_chat_model
oven.muffin_sugar["short_term_memory"] = get_short_term_memory
oven.muffin_sugar["long_term_memory"] = get_long_term_memory
oven.muffin_sugar["rag"] = get_rag
