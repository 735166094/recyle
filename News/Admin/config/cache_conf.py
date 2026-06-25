import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis 连接配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# Redis 客户端实例（异步）
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,  # 自动将字节响应解码为字符串
)


async def get_cache(key: str):
    """
    从 Redis 中获取指定键的缓存值（字符串格式）。

    Args:
        key: 缓存键名（字符串）。

    Returns:
        str | None: 如果键存在则返回对应的字符串值，否则返回 None。
                     若发生异常（如网络问题），返回 None 并打印错误日志。
    """
    logger.debug(f"获取缓存: {key}")
    try:
        return await redis_client.get(key)
    except Exception as e:
        logger.error(f"获取缓存失败: {e}")
        # print(f"获取缓存失败: {e}")
        return None


async def get_json_cache(key: str):
    """
    从 Redis 中获取指定键的 JSON 缓存值，并自动反序列化为 Python 对象（列表或字典）。

    Args:
        key: 缓存键名（字符串）。

    Returns:
        list | dict | None: 如果键存在且内容为合法 JSON，则返回解析后的 Python 对象；
                             如果键不存在，返回 None；若解析失败，返回 None 并打印错误日志。
    """
    logger.debug(f"获取 JSON 缓存: {key}")
    try:
        json_str = await redis_client.get(key)
        if json_str:
            return json.loads(json_str)
            logger.debug(f"获取 JSON 缓存成功: {key}")
        else:
            return None
    except Exception as e:
        print(f"获取 JSON 缓存失败: {e}")
        return None


async def set_cache(key: str, value: str | list | dict, expire_time: int = 3600):
    """
    将数据存入 Redis 缓存，并设置过期时间（秒）。

    如果 value 是列表或字典，会自动序列化为 JSON 字符串后存储；
    如果 value 是普通字符串，则直接存储。

    Args:
        key: 缓存键名（字符串）。
        value: 要存储的数据，支持字符串、列表或字典。
        expire_time: 过期时间（秒），默认为 3600 秒（1 小时）。

    Returns:
        bool: 存储成功返回 True，失败返回 False（并打印错误日志）。
    """
    try:
        # 如果 value 是列表或字典，先转换为 JSON 字符串
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        await redis_client.setex(key, expire_time, value)
        return True
    except Exception as e:
        print(f"设置缓存失败: {e}")
        return False
