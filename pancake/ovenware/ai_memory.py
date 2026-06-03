"""
AI 记忆与 RAG 模块

提供可注入的记忆和检索组件：
  short_term_memory    — 会话记忆（按 session_id 隔离）
  long_term_memory     — 长期记忆（跨 agent 共享）
  rag                  — 检索增强生成

存储后端：
  记忆：memory(内存) | redis | mybatis
  RAG：pgvector | redis | mongodb

配置项（YAML）：
  ai.memory.short_term.backend: memory | redis | mybatis
  ai.memory.short_term.table_name: ai_short_term
  ai.memory.long_term.backend: memory | redis | mybatis
  ai.memory.long_term.table_name: ai_long_term
  ai.rag.backend: pgvector | redis | mongodb
  ai.rag.table_name: ai_rag_docs

可选依赖：pip install pancake[ai]
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Optional

from pancake import oven

logger = logging.getLogger(__name__)

import re as _re
_IDENTIFIER_RE = _re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str, kind: str = "identifier") -> str:
    """校验 SQL 标识符，防注入"""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL {kind}: {name!r}")
    return name


# ============================================================
#  记忆存储后端
# ============================================================

class MemoryBackend:
    """
    记忆存储后端基类

    用户可继承重写：
        class MyBackend(MemoryBackend):
            async def save(self, namespace, key, value, ttl=0):
                # 自定义存储逻辑
    """

    async def save(self, namespace: str, key: str, value: Any, ttl: int = 0) -> None:
        """存储数据"""
        raise NotImplementedError

    async def load(self, namespace: str, key: str) -> Any:
        """加载数据"""
        raise NotImplementedError

    async def delete(self, namespace: str, key: str) -> None:
        """删除数据"""
        raise NotImplementedError

    async def list_keys(self, namespace: str, pattern: str = "*") -> list[str]:
        """列出指定命名空间下的所有 key"""
        raise NotImplementedError

    async def search(self, namespace: str, query: str, limit: int = 10) -> list[dict]:
        """搜索数据"""
        raise NotImplementedError

    async def ensure_table(self, table_name: str) -> None:
        """确保表/数据结构存在"""
        pass


class InMemoryBackend(MemoryBackend):
    """
    纯内存后端 — 进程内 dict，重启丢失

    适合开发/测试场景
    """

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, namespace: str, key: str, value: Any, ttl: int = 0) -> None:
        if namespace not in self._store:
            self._store[namespace] = {}
        self._store[namespace][key] = {
            "value": value,
            "expire_at": time.time() + ttl if ttl > 0 else 0,
        }

    async def load(self, namespace: str, key: str) -> Any:
        ns = self._store.get(namespace, {})
        entry = ns.get(key)
        if entry is None:
            return None
        if entry["expire_at"] > 0 and time.time() > entry["expire_at"]:
            del ns[key]
            return None
        return entry["value"]

    async def delete(self, namespace: str, key: str) -> None:
        ns = self._store.get(namespace, {})
        ns.pop(key, None)

    async def list_keys(self, namespace: str, pattern: str = "*") -> list[str]:
        ns = self._store.get(namespace, {})
        if pattern == "*":
            return list(ns.keys())
        import fnmatch
        return [k for k in ns.keys() if fnmatch.fnmatch(k, pattern)]

    async def search(self, namespace: str, query: str, limit: int = 10) -> list[dict]:
        ns = self._store.get(namespace, {})
        results = []
        for key, entry in ns.items():
            val = entry["value"]
            val_str = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
            if query.lower() in val_str.lower() or query.lower() in key.lower():
                results.append({"key": key, "value": val})
                if len(results) >= limit:
                    break
        return results


class RedisBackend(MemoryBackend):
    """
    Redis 后端 — 复用 redis_cache.RedisClient

    持久化，支持多 agent 共享
    """

    def __init__(self, url: str = None, db: int = 0):
        from pancake import settings
        from .redis_cache import RedisClient
        self._client = RedisClient(url=url or settings.get("redis.url"), db=db, key_prefix="")

    def _ns_key(self, namespace: str, key: str) -> str:
        return f"ai:{namespace}:{key}"

    async def save(self, namespace: str, key: str, value: Any, ttl: int = 0) -> None:
        nk = self._ns_key(namespace, key)
        actual_ttl = ttl if ttl > 0 else None
        await self._client.set_json(nk, value, ttl=actual_ttl)

    async def load(self, namespace: str, key: str) -> Any:
        return await self._client.get_json(self._ns_key(namespace, key))

    async def delete(self, namespace: str, key: str) -> None:
        await self._client.delete(self._ns_key(namespace, key))

    async def list_keys(self, namespace: str, pattern: str = "*") -> list[str]:
        prefix = f"ai:{namespace}:"
        full_keys = await self._client.keys(f"{prefix}{pattern}")
        return [k[len(prefix):] for k in full_keys]

    async def search(self, namespace: str, query: str, limit: int = 10) -> list[dict]:
        keys = await self.list_keys(namespace, "*")
        results = []
        for k in keys[:limit * 2]:
            val = await self.load(namespace, k)
            if val is not None:
                val_str = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
                if query.lower() in val_str.lower() or query.lower() in k.lower():
                    results.append({"key": k, "value": val})
                    if len(results) >= limit:
                        break
        return results


class MyBatisBackend(MemoryBackend):
    """
    MyBatis 后端 — 复用 mybatis.connection.get_database()

    持久化，支持多 agent 共享，自动建表
    """

    def __init__(self, table_name: str = "ai_memory"):
        _validate_identifier(table_name, "table")
        self._db = None
        self._table_name = table_name
        self._table_created = False

    async def _get_db(self):
        if self._db is None:
            from .mybatis.connection import get_database
            self._db = get_database()
        return self._db

    async def ensure_table(self) -> None:
        if self._table_created:
            return
        db = await self._get_db()
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                expire_at REAL DEFAULT 0,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                PRIMARY KEY (namespace, key)
            )
        """)
        self._table_created = True
        logger.info(f"记忆表 {self._table_name} 已就绪")

    async def save(self, namespace: str, key: str, value: Any, ttl: int = 0) -> None:
        await self.ensure_table()
        db = await self._get_db()
        data = json.dumps(value, ensure_ascii=False)
        expire_at = time.time() + ttl if ttl > 0 else 0
        await db.execute(
            f"INSERT OR REPLACE INTO {self._table_name} (namespace, key, value, expire_at) "
            f"VALUES (:ns, :key, :val, :exp)",
            {"ns": namespace, "key": key, "val": data, "exp": expire_at},
        )

    async def load(self, namespace: str, key: str) -> Any:
        await self.ensure_table()
        db = await self._get_db()
        row = await db.fetch_one(
            f"SELECT value, expire_at FROM {self._table_name} WHERE namespace = :ns AND key = :key",
            {"ns": namespace, "key": key},
        )
        if row is None:
            return None
        expire_at = row[1] if len(row) > 1 else 0
        if expire_at and expire_at > 0 and time.time() > expire_at:
            await self.delete(namespace, key)
            return None
        return json.loads(row[0])

    async def delete(self, namespace: str, key: str) -> None:
        await self.ensure_table()
        db = await self._get_db()
        await db.execute(
            f"DELETE FROM {self._table_name} WHERE namespace = :ns AND key = :key",
            {"ns": namespace, "key": key},
        )

    async def list_keys(self, namespace: str, pattern: str = "*") -> list[str]:
        await self.ensure_table()
        db = await self._get_db()
        sql_pattern = pattern.replace("*", "%")
        rows = await db.fetch_all(
            f"SELECT key FROM {self._table_name} WHERE namespace = :ns AND key LIKE :pat",
            {"ns": namespace, "pat": sql_pattern},
        )
        return [row[0] for row in rows]

    async def search(self, namespace: str, query: str, limit: int = 10) -> list[dict]:
        await self.ensure_table()
        db = await self._get_db()
        rows = await db.fetch_all(
            f"SELECT key, value FROM {self._table_name} "
            f"WHERE namespace = :ns AND (key LIKE :q1 OR value LIKE :q2) LIMIT :lim",
            {"ns": namespace, "q1": f"%{query}%", "q2": f"%{query}%", "lim": limit},
        )
        return [{"key": row[0], "value": json.loads(row[1])} for row in rows]


def _create_memory_backend(config: dict) -> MemoryBackend:
    """根据配置创建记忆后端"""
    backend = config.get("backend", "memory")
    table_name = config.get("table_name", "ai_memory")
    if backend == "redis":
        from pancake import settings
        return RedisBackend(
            url=config.get("redis_url", settings.get("redis.url")),
            db=config.get("redis_db", settings.get("redis.db")),
        )
    elif backend == "mybatis":
        return MyBatisBackend(table_name=table_name)
    else:
        return InMemoryBackend()


# ============================================================
#  短期记忆 — 会话记忆（按 session_id 隔离）
# ============================================================

class ShortTermMemory:
    """
    会话记忆 — 按 session_id 隔离的对话上下文

    使用方法：
        await short_term_memory.add("session_001", "user", "你好")
        await short_term_memory.add("session_001", "assistant", "你好！")
        messages = await short_term_memory.get_messages("session_001")
    """

    def __init__(self, backend: MemoryBackend, config: dict):
        self._backend = backend
        self._table_name = config.get("table_name", "ai_short_term")
        self._max_messages = config.get("max_messages", 20)
        self._ttl = config.get("ttl", 86400)

    def _ns(self, session_id: str) -> str:
        return f"stm:{session_id}"

    async def add(self, session_id: str, role: str, content: str) -> None:
        """添加消息到指定会话"""
        ns = self._ns(session_id)
        messages = await self._backend.load(ns, "messages") or []
        messages.append({"role": role, "content": content})

        # 滑动窗口
        if len(messages) > self._max_messages:
            messages = self.on_overflow(messages)

        await self._backend.save(ns, "messages", messages, ttl=self._ttl)

    async def get_messages(self, session_id: str) -> list[dict]:
        """获取指定会话的全部消息"""
        ns = self._ns(session_id)
        return await self._backend.load(ns, "messages") or []

    async def clear(self, session_id: str) -> None:
        """清空指定会话"""
        ns = self._ns(session_id)
        await self._backend.delete(ns, "messages")

    async def list_sessions(self) -> list[str]:
        """列出所有会话"""
        keys = await self._backend.list_keys("stm:*")
        sessions = set()
        for key in keys:
            parts = key.split(":", 1)
            if len(parts) == 2:
                sessions.add(parts[1].rsplit(":", 1)[0] if ":" in parts[1] else parts[1])
        return list(sessions)

    def on_overflow(self, messages: list[dict]) -> list[dict]:
        """
        溢出处理 — 用户可重写

        默认：保留最近 max_messages 条
        """
        return messages[-self._max_messages:]


# ============================================================
#  长期记忆 — 跨 agent 共享
# ============================================================

class LongTermMemory:
    """
    长期记忆 — 跨 agent 共享的持久化记忆

    使用方法：
        await long_term_memory.remember("user_name", "小明")
        name = await long_term_memory.recall("user_name")
        await long_term_memory.forget("user_name")
    """

    def __init__(self, backend: MemoryBackend, config: dict):
        self._backend = backend
        self._table_name = config.get("table_name", "ai_long_term")
        self._ttl = config.get("ttl", 0)

    async def remember(self, key: str, value: Any, ttl: int = None) -> None:
        """存储记忆"""
        actual_ttl = ttl if ttl is not None else self._ttl
        await self._backend.save("ltm", key, value, ttl=actual_ttl)

    async def recall(self, key: str) -> Any:
        """召回记忆"""
        return await self._backend.load("ltm", key)

    async def forget(self, key: str) -> None:
        """删除记忆"""
        await self._backend.delete("ltm", key)

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """搜索记忆"""
        return await self._backend.search("ltm", query, limit=limit)

    async def list_keys(self, pattern: str = "*") -> list[str]:
        """列出所有记忆 key"""
        return await self._backend.list_keys("ltm", pattern)


# ============================================================
#  向量存储后端
# ============================================================

class VectorBackend:
    """
    向量存储后端基类

    用户可继承重写：
        class MyVector(VectorBackend):
            async def add(self, id, embedding, text, metadata=None):
                # 自定义存储
    """

    async def add(self, id: str, embedding: list[float], text: str,
                  metadata: dict = None) -> None:
        """添加向量文档"""
        raise NotImplementedError

    async def query(self, embedding: list[float], top_k: int = 5) -> list[dict]:
        """向量相似度搜索"""
        raise NotImplementedError

    async def delete(self, ids: list[str] = None, where: dict = None) -> None:
        """删除文档"""
        raise NotImplementedError

    async def ensure_collection(self, collection_name: str, dimension: int = 1536) -> None:
        """确保向量集合/表存在"""
        raise NotImplementedError

    async def count(self, collection_name: str = None) -> int:
        """文档数量"""
        raise NotImplementedError


class PgVectorBackend(VectorBackend):
    """
    PostgreSQL pgvector 后端

    复用 mybatis.connection 的数据库连接
    """

    def __init__(self):
        self._db = None
        self._collections_created: set[str] = set()

    async def _get_db(self):
        if self._db is None:
            from .mybatis.connection import get_database
            self._db = get_database()
        return self._db

    async def ensure_collection(self, collection_name: str, dimension: int = 1536) -> None:
        _validate_identifier(collection_name, "collection")
        if collection_name in self._collections_created:
            return
        db = await self._get_db()
        # 创建 pgvector 扩展
        try:
            await db.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception:
            logger.warning("pgvector 扩展创建失败（可能需要超级用户权限）")
        # 创建表
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {collection_name} (
                id TEXT PRIMARY KEY,
                embedding vector({dimension}),
                text TEXT,
                metadata JSONB DEFAULT '{{}}',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        """)
        # 创建 HNSW 索引
        try:
            await db.execute(f"""
                CREATE INDEX IF NOT EXISTS {collection_name}_embedding_idx
                ON {collection_name} USING hnsw (embedding vector_cosine_ops)
            """)
        except Exception:
            pass
        self._collections_created.add(collection_name)
        logger.info(f"pgvector 集合 {collection_name} 已就绪")

    async def add(self, id: str, embedding: list[float], text: str,
                  metadata: dict = None, collection_name: str = "ai_rag") -> None:
        await self.ensure_collection(collection_name, len(embedding))
        db = await self._get_db()
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        await db.execute(
            f"INSERT INTO {collection_name} (id, embedding, text, metadata) "
            f"VALUES (:id, :emb::vector, :text, :meta::jsonb)",
            {"id": id, "emb": embedding_str, "text": text, "meta": meta_json},
        )

    async def query(self, embedding: list[float], top_k: int = 5,
                    collection_name: str = "ai_rag") -> list[dict]:
        await self.ensure_collection(collection_name, len(embedding))
        db = await self._get_db()
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        rows = await db.fetch_all(
            f"SELECT id, text, metadata, 1 - (embedding <=> :emb::vector) as score "
            f"FROM {collection_name} ORDER BY embedding <=> :emb::vector LIMIT :k",
            {"emb": embedding_str, "k": top_k},
        )
        return [
            {
                "id": row[0],
                "text": row[1],
                "metadata": json.loads(row[2]) if row[2] else {},
                "score": row[3],
            }
            for row in rows
        ]

    async def delete(self, ids: list[str] = None, where: dict = None,
                     collection_name: str = "ai_rag") -> None:
        _validate_identifier(collection_name, "collection")
        db = await self._get_db()
        if ids:
            placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
            values = {f"id_{i}": id for i, id in enumerate(ids)}
            await db.execute(
                f"DELETE FROM {collection_name} WHERE id IN ({placeholders})", values
            )
        elif where:
            for k in where:
                _validate_identifier(k, "column")
            conditions = " AND ".join(f"{k} = :{k}" for k in where)
            await db.execute(
                f"DELETE FROM {collection_name} WHERE {conditions}", where
            )

    async def count(self, collection_name: str = "ai_rag") -> int:
        db = await self._get_db()
        row = await db.fetch_one(f"SELECT COUNT(*) FROM {collection_name}")
        return row[0] if row else 0


class RedisVectorBackend(VectorBackend):
    """
    Redis RediSearch 向量后端

    复用 redis_cache.RedisClient
    """

    def __init__(self, url: str = None, db: int = 0):
        from pancake import settings
        from .redis_cache import RedisClient
        self._client = RedisClient(url=url or settings.get("redis.url"), db=db, key_prefix="")
        self._redis = None
        self._collections_created: set[str] = set()

    async def _get_redis(self):
        if self._redis is None:
            self._redis = await self._client._get_conn()
        return self._redis

    async def ensure_collection(self, collection_name: str, dimension: int = 1536) -> None:
        if collection_name in self._collections_created:
            return
        redis = await self._get_redis()
        try:
            await redis.ft(collection_name).info()
            self._collections_created.add(collection_name)
            return
        except Exception:
            pass

        from redis.commands.search.field import VectorField, TextField, NumericField
        from redis.commands.search.index_definition import IndexDefinition, IndexType

        schema = [
            TextField("text"),
            TextField("metadata"),
            NumericField("created_at"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": dimension,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        ]
        definition = IndexDefinition(prefix=[f"{collection_name}:"], index_type=IndexType.HASH)
        await redis.ft(collection_name).create_index(schema, definition=definition)
        self._collections_created.add(collection_name)
        logger.info(f"Redis 向量集合 {collection_name} 已就绪")

    async def add(self, id: str, embedding: list[float], text: str,
                  metadata: dict = None, collection_name: str = "ai_rag") -> None:
        await self.ensure_collection(collection_name, len(embedding))
        redis = await self._get_redis()
        import struct
        emb_bytes = struct.pack(f"{len(embedding)}f", *embedding)
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        await redis.hset(
            f"{collection_name}:{id}",
            mapping={
                "text": text,
                "metadata": meta_json,
                "embedding": emb_bytes,
                "created_at": str(time.time()),
            },
        )

    async def query(self, embedding: list[float], top_k: int = 5,
                    collection_name: str = "ai_rag") -> list[dict]:
        await self.ensure_collection(collection_name, len(embedding))
        redis = await self._get_redis()
        import struct
        emb_bytes = struct.pack(f"{len(embedding)}f", *embedding)

        from redis.commands.search.query import Query
        query = (
            Query(f"*=>[KNN {top_k} @embedding $vec AS score]")
            .sort_by("score")
            .return_fields("text", "metadata", "score")
            .dialect(2)
        )
        results = await redis.ft(collection_name).search(
            query, query_params={"vec": emb_bytes}
        )

        docs = []
        for doc in results.docs:
            docs.append({
                "id": doc.id.replace(f"{collection_name}:", ""),
                "text": doc.text,
                "metadata": json.loads(getattr(doc, "metadata", "{}") or "{}"),
                "score": float(getattr(doc, "score", 0)),
            })
        return docs

    async def delete(self, ids: list[str] = None, where: dict = None,
                     collection_name: str = "ai_rag") -> None:
        redis = await self._get_redis()
        if ids:
            for id in ids:
                await redis.delete(f"{collection_name}:{id}")

    async def count(self, collection_name: str = "ai_rag") -> int:
        redis = await self._get_redis()
        info = await redis.ft(collection_name).info()
        return int(info.get("num_docs", 0))


class MongoVectorBackend(VectorBackend):
    """
    MongoDB Atlas Vector Search 后端
    """

    def __init__(self, url: str = None, db_name: str = None):
        from pancake import settings
        self._url = url or settings.get("mongo.url")
        self._db_name = db_name or settings.get("mongo.db")
        self._client = None
        self._db = None
        self._collections_created: set[str] = set()

    async def _get_db(self):
        if self._db is None:
            import pymongo
            self._client = pymongo.AsyncMongoClient(self._url)
            self._db = self._client[self._db_name]
        return self._db

    async def ensure_collection(self, collection_name: str, dimension: int = 1536) -> None:
        if collection_name in self._collections_created:
            return
        db = await self._get_db()
        existing = await db.list_collection_names()
        if collection_name not in existing:
            await db.create_collection(collection_name)
            # 创建向量搜索索引
            collection = db[collection_name]
            await collection.create_index(
                [("embedding", "vectorSearch")],
                name=f"{collection_name}_vector_idx",
                vectorSearchOptions={
                    "dimensions": dimension,
                    "similarity": "cosine",
                },
            )
        self._collections_created.add(collection_name)
        logger.info(f"MongoDB 向量集合 {collection_name} 已就绪")

    async def add(self, id: str, embedding: list[float], text: str,
                  metadata: dict = None, collection_name: str = "ai_rag") -> None:
        await self.ensure_collection(collection_name, len(embedding))
        db = await self._get_db()
        collection = db[collection_name]
        await collection.replace_one(
            {"_id": id},
            {
                "_id": id,
                "text": text,
                "metadata": metadata or {},
                "embedding": embedding,
                "created_at": time.time(),
            },
            upsert=True,
        )

    async def query(self, embedding: list[float], top_k: int = 5,
                    collection_name: str = "ai_rag") -> list[dict]:
        await self.ensure_collection(collection_name, len(embedding))
        db = await self._get_db()
        collection = db[collection_name]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": f"{collection_name}_vector_idx",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": top_k * 10,
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "text": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        results = []
        async for doc in collection.aggregate(pipeline):
            results.append({
                "id": doc["_id"],
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0),
            })
        return results

    async def delete(self, ids: list[str] = None, where: dict = None,
                     collection_name: str = "ai_rag") -> None:
        db = await self._get_db()
        collection = db[collection_name]
        if ids:
            await collection.delete_many({"_id": {"$in": ids}})
        elif where:
            await collection.delete_many(where)

    async def count(self, collection_name: str = "ai_rag") -> int:
        db = await self._get_db()
        return await db[collection_name].count_documents({})


def _create_vector_backend(config: dict) -> VectorBackend:
    """根据配置创建向量后端"""
    from pancake import settings
    backend = config.get("backend", "pgvector")
    if backend == "pgvector":
        return PgVectorBackend()
    elif backend == "redis":
        return RedisVectorBackend(
            url=config.get("redis_url", settings.get("redis.url")),
            db=config.get("redis_db", settings.get("redis.db")),
        )
    elif backend == "mongodb":
        url = config.get("mongo_url", settings.get("mongo.url"))
        if isinstance(url, str) and url.startswith("${"):
            url = os.environ.get(url[2:-1], settings.get("mongo.url"))
        db_name = config.get("mongo_db", settings.get("mongo.db"))
        return MongoVectorBackend(url=url, db_name=db_name)
    else:
        raise ValueError(f"不支持的 RAG 后端: {backend}，支持: pgvector, redis, mongodb")


# ============================================================
#  RAG — 检索增强生成
# ============================================================

class RAG:
    """
    检索增强生成

    使用方法：
        await rag.add_document("Pancake 是一个 Python 框架...")
        results = await rag.query("什么是 Pancake？")
        answer = await rag.ask("什么是 Pancake？")
    """

    def __init__(self, vector_backend: VectorBackend, config: dict):
        self._backend = vector_backend
        self._collection_name = config.get("table_name", "ai_rag_docs")
        self._chunk_size = config.get("chunk_size", 500)
        self._chunk_overlap = config.get("chunk_overlap", 50)
        self._top_k = config.get("top_k", 5)
        self._embedding_provider = config.get("embedding_provider")
        self._dimension = config.get("dimension", 1536)

    async def _get_embedding(self, text: str) -> list[float]:
        """获取文本向量 — 调用 chat_model.embed()"""
        from .ai_model import get_chat_model
        chat_model = get_chat_model()
        if chat_model is None:
            raise RuntimeError("chat_model 未初始化，无法生成向量")
        return await chat_model.embed(text, model=self._embedding_provider)

    def _chunk_text(self, text: str) -> list[str]:
        """文本分块"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            chunks.append(text[start:end])
            start += self._chunk_size - self._chunk_overlap
        return chunks

    async def add_document(self, text: str, metadata: dict = None) -> None:
        """添加文档（自动分块 + 向量化）"""
        await self._backend.ensure_collection(self._collection_name, self._dimension)
        chunks = self._chunk_text(text)
        count = await self._backend.count(self._collection_name)

        for i, chunk in enumerate(chunks):
            embedding = await self._get_embedding(chunk)
            doc_id = f"doc_{count + 1}_{i}"
            meta = {"chunk_index": i, "total_chunks": len(chunks)}
            if metadata:
                meta.update(metadata)

            await self._backend.add(
                id=doc_id, embedding=embedding, text=chunk,
                metadata=meta, collection_name=self._collection_name,
            )

        logger.info(f"添加文档: {len(chunks)} 个分块")

    async def add_documents(self, docs: list[dict]) -> None:
        """批量添加文档 [{"text": "...", "metadata": {...}}, ...]"""
        for doc in docs:
            await self.add_document(doc["text"], doc.get("metadata"))

    async def query(self, question: str, top_k: int = None) -> list[dict]:
        """检索相关文档"""
        embedding = await self._get_embedding(question)
        k = top_k or self._top_k
        return await self._backend.query(embedding, top_k=k,
                                         collection_name=self._collection_name)

    async def ask(self, question: str, model: str = None,
                  system_prompt: str = None) -> str:
        """RAG 问答（检索 + 生成）"""
        from .ai_model import get_chat_model
        chat_model = get_chat_model()
        if chat_model is None:
            raise RuntimeError("chat_model 未初始化，无法 RAG 问答")

        docs = await self.query(question)
        messages = self.build_prompt(question, docs, system_prompt)
        return await chat_model.chat(messages, model=model)

    def build_prompt(self, question: str, context: list[dict],
                     system_prompt: str = None) -> list[dict]:
        """
        构建 prompt — 用户可重写

        Args:
            question: 用户问题
            context: 检索到的文档
            system_prompt: 自定义 system prompt
        """
        context_text = "\n\n".join(
            f"[资料{i+1}] {doc['text']}" for i, doc in enumerate(context)
        )
        sys_prompt = system_prompt or (
            "你是一个智能助手。请根据以下参考资料回答用户的问题。"
            "如果资料中没有相关信息，请如实说明。\n\n"
            f"参考资料：\n{context_text}"
        )
        return [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": question},
        ]

    async def delete(self, ids: list[str] = None, where: dict = None) -> None:
        """删除文档"""
        await self._backend.delete(ids=ids, where=where,
                                   collection_name=self._collection_name)
