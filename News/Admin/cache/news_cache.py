from typing import List, Dict, Any, Optional

from config.cache_conf import get_json_cache, set_cache

CATEGORIES_KEY = "news:categories"  # Redis 键名常量，用于存储新闻分类缓存
NEWS_LIST_PREFIX = "news:list:"


async def get_cache_categories():
    """
    从 Redis 缓存中获取新闻分类数据。

    该函数直接调用 `get_json_cache`，自动将存储的 JSON 字符串反序列化为 Python 对象。

    Returns:
        List[Dict[str, Any]] | None: 如果缓存存在，返回分类列表（每个分类为字典）；
                                     如果缓存不存在或解析失败，返回 None。
    """
    return await get_json_cache(CATEGORIES_KEY)


async def set_cache_categories(data: List[Dict[str, Any]], expire: int = 7200):
    """
    将新闻分类数据存入 Redis 缓存。

    数据会被序列化为 JSON 字符串，并设置过期时间（默认 7200 秒，即 2 小时）。

    Args:
        data: 新闻分类列表，每个元素为包含分类信息的字典（如 id、name 等）。
        expire: 缓存过期时间（秒），默认 7200 秒。

    Returns:
        bool: 存储成功返回 True，失败返回 False（错误日志已在 `set_cache` 内部打印）。
    """
    return await set_cache(CATEGORIES_KEY, data, expire)


async def get_cache_news_list(category_id: Optional[int], page: int, page_size: int):
    """
    从 Redis 缓存中获取指定分类下的新闻列表（分页缓存）。

    键名规则：news:list:{category_id或all}:{page}:{page_size}
    例如：news:list:5:1:10 表示分类ID=5，第1页，每页10条

    Args:
        category_id: 新闻分类 ID，若为 None 则表示获取“全部”分类新闻。
        page: 当前页码（从 1 开始）。
        page_size: 每页新闻数量。

    Returns:
        List[Dict[str, Any]] | None: 如果缓存存在，返回新闻列表（每个新闻为字典）；
                                     如果缓存不存在或解析失败，返回 None。
    """
    # 如果 category_id 为 None，使用 "all" 表示全部分类
    category_part = category_id if category_id is not None else "all"
    # 构建缓存键名
    key = f"{NEWS_LIST_PREFIX}{category_part}:{page}:{page_size}"
    # 从 Redis 获取 JSON 缓存并自动反序列化
    return await get_json_cache(key)


async def set_cache_news_list(data: List[Dict[str, Any]], category_id: Optional[int], page: int, page_size: int,
                              expire: int = 7200) -> bool:
    """
    将指定分类下的新闻列表数据存入 Redis 缓存。

    键名规则与 get_cache_news_list 一致，确保读写使用相同的键。

    Args:
        data: 新闻列表数据（字典列表），需要可 JSON 序列化。
        category_id: 新闻分类 ID，若为 None 则表示存储“全部”分类。
        page: 当前页码。
        page_size: 每页数量。
        expire: 缓存过期时间（秒），默认 7200 秒（2 小时）。

    Returns:
        bool: 存储成功返回 True，失败返回 False（错误日志在 set_cache 内部打印）。
    """
    # 如果 category_id 为 None，使用 "all" 表示全部分类
    category_part = category_id if category_id is not None else "all"
    # 构建缓存键名（与 get_cache_news_list 保持一致）
    key = f"{NEWS_LIST_PREFIX}{category_part}:{page}:{page_size}"
    # 存储数据（set_cache 内部会自动将 list/dict 序列化为 JSON）
    return await set_cache(key, data, expire)
