"""
Redis 缓存插件
提供缓存操作、Hash/List/Set 数据结构、JSON 存储、装饰器缓存

配置项（YAML 或 XML）：
  redis.url: redis://localhost:6379
  redis.db: 0
  redis.password: null
  redis.key_prefix: "pancake:"
  redis.default_ttl: 3600

可选依赖：pip install pancake[redis]
"""

import asyncio
import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional

from pancake import oven
from pancake.ovenware import check_dependencies

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装"""

    def __init__(self, url: str = "redis://localhost:6379", db: int = 0,
                 password: str = None, key_prefix: str = "pancake:",
                 default_ttl: int = 3600):
        self.url = url
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self._redis = None

    async def _get_conn(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.url, db=self.db, password=self.password,
                decode_responses=True
            )
        return self._redis

    def _key(self, key: str) -> str:
        """添加 key 前缀"""
        if key.startswith(self.key_prefix):
            return key
        return f"{self.key_prefix}{key}"

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None

    # ============================================================
    #  基础缓存操作
    # ============================================================

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        conn = await self._get_conn()
        return await conn.get(self._key(key))

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置值，可选过期时间（秒）"""
        conn = await self._get_conn()
        k = self._key(key)
        if ttl is None:
            ttl = self.default_ttl
        if ttl and ttl > 0:
            await conn.set(k, value, ex=ttl)
        else:
            await conn.set(k, value)

    async def delete(self, *keys: str) -> int:
        """删除一个或多个 key"""
        conn = await self._get_conn()
        return await conn.delete(*[self._key(k) for k in keys])

    async def exists(self, key: str) -> bool:
        """检查 key 是否存在"""
        conn = await self._get_conn()
        return bool(await conn.exists(self._key(key)))

    async def ttl(self, key: str) -> int:
        """获取 key 剩余过期时间（秒），-1 永不过期，-2 不存在"""
        conn = await self._get_conn()
        return await conn.ttl(self._key(key))

    async def expire(self, key: str, seconds: int) -> bool:
        """设置 key 过期时间"""
        conn = await self._get_conn()
        return await conn.expire(self._key(key), seconds)

    async def incr(self, key: str, amount: int = 1) -> int:
        """自增"""
        conn = await self._get_conn()
        return await conn.incrby(self._key(key), amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """自减"""
        conn = await self._get_conn()
        return await conn.decrby(self._key(key), amount)

    async def keys(self, pattern: str = "*") -> list[str]:
        """按模式搜索 key"""
        conn = await self._get_conn()
        full_keys = await conn.keys(self._key(pattern))
        prefix_len = len(self.key_prefix)
        return [k[prefix_len:] for k in full_keys]

    async def clear_prefix(self, prefix: str) -> int:
        """删除指定前缀的所有 key"""
        keys = await self.keys(f"{prefix}*")
        if keys:
            return await self.delete(*keys)
        return 0

    # ============================================================
    #  JSON 存储
    # ============================================================

    async def get_json(self, key: str) -> Any:
        """获取 JSON 对象"""
        data = await self.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def set_json(self, key: str, value: Any, ttl: int = None) -> None:
        """存储 JSON 对象"""
        await self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    # ============================================================
    #  Hash 操作
    # ============================================================

    async def hget(self, key: str, field: str) -> Optional[str]:
        """获取 hash 字段值"""
        conn = await self._get_conn()
        return await conn.hget(self._key(key), field)

    async def hset(self, key: str, field: str = None, value: Any = None,
                   mapping: dict = None) -> int:
        """设置 hash 字段"""
        conn = await self._get_conn()
        if mapping:
            return await conn.hset(self._key(key), mapping=mapping)
        return await conn.hset(self._key(key), field, value)

    async def hdel(self, key: str, *fields: str) -> int:
        """删除 hash 字段"""
        conn = await self._get_conn()
        return await conn.hdel(self._key(key), *fields)

    async def hgetall(self, key: str) -> dict:
        """获取 hash 所有字段"""
        conn = await self._get_conn()
        return await conn.hgetall(self._key(key))

    async def hkeys(self, key: str) -> list[str]:
        """获取 hash 所有字段名"""
        conn = await self._get_conn()
        return await conn.hkeys(self._key(key))

    async def hvals(self, key: str) -> list[str]:
        """获取 hash 所有值"""
        conn = await self._get_conn()
        return await conn.hvals(self._key(key))

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """hash 字段自增"""
        conn = await self._get_conn()
        return await conn.hincrby(self._key(key), field, amount)

    # ============================================================
    #  List 操作
    # ============================================================

    async def lpush(self, key: str, *values: Any) -> int:
        """左侧推入"""
        conn = await self._get_conn()
        return await conn.lpush(self._key(key), *values)

    async def rpush(self, key: str, *values: Any) -> int:
        """右侧推入"""
        conn = await self._get_conn()
        return await conn.rpush(self._key(key), *values)

    async def lpop(self, key: str) -> Optional[str]:
        """左侧弹出"""
        conn = await self._get_conn()
        return await conn.lpop(self._key(key))

    async def rpop(self, key: str) -> Optional[str]:
        """右侧弹出"""
        conn = await self._get_conn()
        return await conn.rpop(self._key(key))

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """获取列表范围"""
        conn = await self._get_conn()
        return await conn.lrange(self._key(key), start, end)

    async def llen(self, key: str) -> int:
        """获取列表长度"""
        conn = await self._get_conn()
        return await conn.llen(self._key(key))

    # ============================================================
    #  Set 操作
    # ============================================================

    async def sadd(self, key: str, *values: Any) -> int:
        """添加集合成员"""
        conn = await self._get_conn()
        return await conn.sadd(self._key(key), *values)

    async def srem(self, key: str, *values: Any) -> int:
        """删除集合成员"""
        conn = await self._get_conn()
        return await conn.srem(self._key(key), *values)

    async def smembers(self, key: str) -> set:
        """获取集合所有成员"""
        conn = await self._get_conn()
        return await conn.smembers(self._key(key))

    async def sismember(self, key: str, value: Any) -> bool:
        """检查是否是集合成员"""
        conn = await self._get_conn()
        return await conn.sismember(self._key(key), value)

    async def scard(self, key: str) -> int:
        """获取集合大小"""
        conn = await self._get_conn()
        return await conn.scard(self._key(key))

    # ============================================================
    #  分布式锁
    # ============================================================

    async def lock(self, name: str, timeout: int = 10, blocking: bool = True,
                   blocking_timeout: int = 10) -> Optional["RedisLock"]:
        """获取分布式锁"""
        conn = await self._get_conn()
        lock_key = self._key(f"lock:{name}")
        lock = RedisLock(conn, lock_key, timeout=timeout)

        if blocking:
            acquired = await lock.acquire(blocking_timeout=blocking_timeout)
            if acquired:
                return lock
            return None
        else:
            acquired = await lock.acquire(blocking_timeout=0)
            if acquired:
                return lock
            return None


class RedisLock:
    """分布式锁"""

    def __init__(self, conn, key: str, timeout: int = 10):
        self._conn = conn
        self._key = key
        self._timeout = timeout
        self._token = None

    async def acquire(self, blocking_timeout: int = 10) -> bool:
        import secrets
        self._token = secrets.token_hex(16)
        end_time = asyncio.get_event_loop().time() + blocking_timeout
        while True:
            if await self._conn.set(self._key, self._token, nx=True, ex=self._timeout):
                return True
            if asyncio.get_event_loop().time() >= end_time:
                return False
            await asyncio.sleep(0.05)

    async def release(self) -> None:
        if self._token:
            # Lua 脚本保证原子性
            lua = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self._conn.eval(lua, 1, self._key, self._token)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


# ============================================================
#  缓存防护
# ============================================================

# 空值标记，防止缓存穿透
_NULL_PLACEHOLDER = "__PANCAKE_NULL__"

# 单飞锁，防止缓存击穿
_singleflight_locks: dict[str, asyncio.Lock] = {}


class CacheGuard:
    """
    缓存防护工具

    防穿透：查询不存在的数据时，缓存空值标记，短 TTL
    防雪崩：TTL 加随机偏移，避免同时过期
    防击穿：热 key 过期时，用锁保证只有一个请求回源
    """

    def __init__(self, client: "RedisClient"):
        self._client = client

    async def get_or_load(self, key: str, loader: Callable,
                          ttl: int = None, null_ttl: int = 30,
                          jitter: int = 0, protect_breakdown: bool = True) -> Any:
        """
        获取缓存，未命中则调用 loader 回源

        防穿透：loader 返回 None 时，缓存空值标记 null_ttl 秒
        防雪崩：jitter > 0 时，TTL 加随机偏移 [0, jitter)
        防击穿：protect_breakdown=True 时，用锁防止并发回源

        Args:
            key: 缓存 key
            loader: 回源函数（async 或 sync）
            ttl: 缓存过期时间（秒）
            null_ttl: 空值缓存时间（秒），防止穿透
            jitter: TTL 随机偏移上限（秒），防止雪崩
            protect_breakdown: 是否防击穿（单飞锁）

        Returns:
            缓存值或 loader 返回值
        """
        # 1. 先查缓存
        data = await self._client.get(key)

        # 命中空值标记
        if data == _NULL_PLACEHOLDER:
            logger.debug(f"缓存空值命中: {key}")
            return None

        # 命中正常值
        if data is not None:
            logger.debug(f"缓存命中: {key}")
            return await self._client.get_json(key)

        # 2. 未命中，准备回源
        if protect_breakdown:
            # 防击穿：单飞锁
            lock_key = f"_sf:{key}"
            if lock_key not in _singleflight_locks:
                _singleflight_locks[lock_key] = asyncio.Lock()
            lock = _singleflight_locks[lock_key]

            async with lock:
                # 双重检查：拿到锁后再查一次
                data = await self._client.get(key)
                if data == _NULL_PLACEHOLDER:
                    return None
                if data is not None:
                    return await self._client.get_json(key)

                # 回源
                result = await self._call_loader(loader)
                await self._store(key, result, ttl, null_ttl, jitter)
                return result
        else:
            # 不防击穿，直接回源
            result = await self._call_loader(loader)
            await self._store(key, result, ttl, null_ttl, jitter)
            return result

    async def _call_loader(self, loader: Callable) -> Any:
        """调用回源函数"""
        if asyncio.iscoroutinefunction(loader):
            return await loader()
        return loader()

    async def _store(self, key: str, result: Any, ttl: int, null_ttl: int, jitter: int):
        """存储结果到缓存"""
        # 计算实际 TTL（加随机偏移防雪崩）
        import random
        actual_ttl = ttl
        if actual_ttl and jitter > 0:
            actual_ttl = actual_ttl + random.randint(0, jitter - 1)

        if result is None:
            # 防穿透：缓存空值标记
            await self._client.set(key, _NULL_PLACEHOLDER, ttl=null_ttl)
            logger.debug(f"缓存空值写入: {key} (ttl={null_ttl}s)")
        else:
            await self._client.set_json(key, result, ttl=actual_ttl)
            logger.debug(f"缓存写入: {key} (ttl={actual_ttl}s)")

    async def invalidate(self, key: str) -> None:
        """主动失效缓存"""
        await self._client.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """按模式失效缓存"""
        return await self._client.clear_prefix(pattern)


# ============================================================
#  缓存装饰器
# ============================================================

def cached(key: str = None, ttl: int = None, prefix: str = "cache",
           null_ttl: int = 30, jitter: int = 0, protect_breakdown: bool = True):
    """
    缓存装饰器 — 自动缓存函数返回值，内置三重防护

    防穿透：函数返回 None 时，缓存空值标记 null_ttl 秒
    防雪崩：jitter > 0 时，TTL 加随机偏移
    防击穿：protect_breakdown=True 时，用锁防止并发回源

    使用方法：
        @cached(ttl=300)
        async def get_user(user_id: int):
            return await db.query(user_id)

        @cached(key="user:{user_id}", ttl=600, jitter=60)
        async def get_user_detail(user_id: int):
            return await db.query_detail(user_id)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            client = _manager.get()
            if client is None:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            guard = CacheGuard(client)

            # 构建缓存 key
            if key:
                cache_key = key.format(**kwargs, **{str(i): v for i, v in enumerate(args)})
            else:
                func_name = func.__qualname__
                params = f"{args}:{kwargs}"
                param_hash = hashlib.md5(params.encode()).hexdigest()[:8]
                cache_key = f"{prefix}:{func_name}:{param_hash}"

            # 使用 get_or_load，自动处理穿透/雪崩/击穿
            async def loader():
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            return await guard.get_or_load(
                cache_key, loader,
                ttl=ttl, null_ttl=null_ttl,
                jitter=jitter, protect_breakdown=protect_breakdown
            )

        wrapper._cache_clear = lambda: _manager.get().clear_prefix(prefix) if _manager.get() else None
        return wrapper
    return decorator


# ============================================================
#  Redis 管理器
# ============================================================


class RedisManager:
    """
    Redis 管理器 — 封装全局 Redis 客户端状态

    使用方法:
        manager = RedisManager()
        manager.set(RedisClient("redis://localhost:6379"))
        client = manager.get()
        manager.reset()
    """

    def __init__(self):
        self._client: Optional[RedisClient] = None

    def get(self) -> Optional[RedisClient]:
        """获取全局 Redis 客户端"""
        return self._client

    def set(self, client: RedisClient) -> None:
        """设置全局 Redis 客户端"""
        self._client = client

    def reset(self) -> None:
        """重置状态（用于测试）"""
        self._client = None


# 向后兼容的模块级默认实例
_manager = RedisManager()

get_client = _manager.get
set_client = _manager.set


def create_manager() -> RedisManager:
    """创建新的独立管理器（用于测试）"""
    return RedisManager()


# ============================================================
#  插件 Main 类
# ============================================================

class Main(InitAction):
    """Redis 插件主类"""

    init_order = 2  # 在 mybatis 之后，web 之前
    _dependencies = ["redis"]
    _extras = "redis"

    def __init__(self):
        url = oven.pancake_yaml.get("redis.url", "redis://localhost:6379")
        db = oven.pancake_yaml.get("redis.db", 0)
        password = oven.pancake_yaml.get("redis.password")
        prefix = oven.pancake_yaml.get("redis.key_prefix", "pancake:")
        default_ttl = oven.pancake_yaml.get("redis.default_ttl", 3600)

        client = RedisClient(
            url=url, db=db, password=password,
            key_prefix=prefix, default_ttl=default_ttl
        )
        _manager.set(client)

        oven.pancake_other["redis"] = client

    @staticmethod
    def check():
        check_dependencies(Main._dependencies, Main._extras)

    def build(self):
        client = _manager.get()
        logger.info(f"Redis 插件构建完成 (url={client.url if client else 'N/A'})")

    async def loop_method(self):
        """测试连接"""
        client = _manager.get()
        if client is None:
            logger.warning("Redis 客户端未初始化")
            return
        try:
            conn = await client._get_conn()
            await conn.ping()
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}")


# 注册到 oven
oven.muffin_flour["cached"] = cached
oven.muffin_flour["RedisClient"] = RedisClient
oven.muffin_flour["CacheGuard"] = CacheGuard
oven.muffin_suger["redis_client"] = get_client
