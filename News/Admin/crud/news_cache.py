from typing import List, Any, Dict

from celery.bin.result import result
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import get_cache_categories, set_cache_categories, get_cache_news_list, set_cache_news_list
from models.news import Category, News
from schemas.base import NewsItemBase


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 10):
    """
    分页查询新闻种类，优先从 Redis 缓存获取（全量缓存，忽略分页参数）。

    注意：
        1. 当前缓存键固定为 "news:categories"，缓存的是全部分类数据（不分页）。
        2. 若缓存命中，则直接返回缓存的字典列表，**忽略** skip 和 limit 参数。
        3. 若缓存未命中，则从数据库按分页查询，并将查询结果（字典列表）缓存。
        4. 由于缓存存储的是 JSON 序列化的字典，返回的数据类型为 List[dict]，
           而非 Category 对象列表。建议调用方按字典处理。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        skip: 分页偏移量，仅在缓存未命中时生效，默认 0。
        limit: 每页最多返回的记录数，仅在缓存未命中时生效，默认 10。

    Returns:
        List[dict]: 分类数据的字典列表，每个字典包含 Category 模型的所有字段。
                    若数据库无数据且缓存未命中，返回空列表。

    Raises:
        SQLAlchemyError: 数据库查询失败时可能抛出（由上层异常处理器处理）。
    """

    # 1. 尝试从缓存获取全部分类数据
    cached_categories = await get_cache_categories()
    if cached_categories is not None:
        # 缓存命中，直接返回（注意：返回的是字典列表）
        return cached_categories

    # 2. 缓存未命中，执行数据库分页查询
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()  # List[Category]

    # 3. 将 ORM 对象转换为可 JSON 序列化的字典列表
    if categories:
        encoded_categories = jsonable_encoder(categories)
        # 异步存入缓存（默认过期时间由 set_cache_categories 控制，通常为 7200 秒）
        await set_cache_categories(encoded_categories)
        return encoded_categories
    else:
        # 若查询为空，也返回空列表，但不缓存空数据（避免缓存穿透）
        return []


async def get_news_list(db: AsyncSession, category_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """
    根据新闻分类 ID 分页查询新闻列表（优先从缓存获取）。

    该函数会先尝试从 Redis 获取对应分页的缓存数据（字典格式），
    若缓存命中则直接返回；否则执行数据库查询，并将结果序列化为字典列表后缓存。

    注意：
        - 缓存键基于 `category_id`、`page`、`limit`（作为 page_size）生成。
        - 为避免分页参数混淆，内部计算 `page = skip // limit + 1`。
        - 返回的数据统一为字典列表，方便前后端交互。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        category_id: 新闻分类的外键 ID，用于筛选指定类别的新闻。
        skip: 分页偏移量，默认为 0（从第一条开始）。
        limit: 每页最多返回的记录条数，默认为 10。

    Returns:
        List[Dict[str, Any]]: 包含新闻数据的字典列表，若该类目下暂无新闻则返回空列表。
        每个字典包含 News 模型的所有字段（通过 Pydantic 模型序列化）。

    Raises:
        SQLAlchemyError: 数据库查询失败时可能抛出（由上层异常处理器处理）。
    """
    # 1. 计算当前页码（缓存键需要使用 page 和 page_size）
    page = skip // limit + 1

    # 2. 尝试从缓存获取
    cached_data = await get_cache_news_list(category_id, page, limit)
    if cached_data is not None:
        # 缓存命中，直接返回字典列表
        return cached_data

    # 3. 缓存未命中，执行数据库分页查询
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    news_list = result.scalars().all()  # List[News]

    # 4. 将 ORM 对象序列化为字典列表（用于缓存和返回）
    if news_list:
        # 使用 Pydantic 模型将每个 News 对象转换为字典（by_alias=False 保持字段名不变）
        news_data = [
            NewsItemBase.model_validate(news).model_dump(mode="json", by_alias=False)
            for news in news_list
        ]
        # 异步存入缓存（默认过期时间 7200 秒，由 set_cache_news_list 内部设定）
        await set_cache_news_list(news_data, category_id, page, limit)
        return news_data
    else:
        # 查询结果为空，返回空列表（不缓存，防止缓存穿透）
        return []


async def get_news_count(db: AsyncSession, category_id: int):
    """
    查询指定分类下的新闻总数量

    :param db: 异步数据库会话对象（AsyncSession），用于执行 SQL 查询
    :param category_id: 新闻分类的外键 ID，用于筛选统计目标分类
    :return: 该分类下的新闻总数（int 类型），即使该分类下没有新闻，COUNT 聚合函数也会返回 0，不会报错
    """
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_news_detail(db: AsyncSession, news_id: int):
    """
    根据新闻ID查询新闻详情

    :param db: 异步数据库会话对象（AsyncSession），用于执行 SQL 查询
    :param news_id: 新闻的 ID，用于查询指定新闻的详情
    :return: 匹配到的新闻对象（News），若没有匹配的记录则返回 None
    """
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def increase_news_view(db: AsyncSession, news_id: int):
    """
    根据新闻ID更新新闻的浏览次数

    :param db: 异步数据库会话对象（AsyncSession），用于执行 SQL 更新
    :param news_id: 新闻的 ID，用于更新指定新闻的浏览次数
    :return: 更新成功返回 True，否则返回 False
    """
    stmt = update(News).where(News.id == news_id).values(view=News.view + 1)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_related_news(db: AsyncSession, news_id: int, category_id: int, limit: int = 3):
    """
    获取与指定新闻相关的其他新闻（同一分类下，排除自身，按发布时间和浏览量排序）

    :param db: 异步数据库会话对象（AsyncSession），用于执行 SQL 查询
    :param news_id: 当前新闻的 ID，用于排除自身
    :param category_id: 新闻分类 ID，确保返回的新闻属于同一分类
    :param limit: 最多返回的相关新闻条数，默认为 3
    :return: 包含相关新闻信息的字典列表（List[dict]），每个字典包含以下字段：
             - id: 新闻 ID
             - title: 标题
             - description: 简介
             - content: 内容
             - image: 图片链接
             - author: 作者
             - publish_time: 发布时间
             - categoryId: 分类 ID
             - views: 浏览量
             若没有其他相关新闻，则返回空列表
    """
    stmt = select(News).where(
        News.category_id == category_id,
        News.id != news_id
    ).order_by(
        News.publish_time.desc(),
        News.views.desc()
    ).limit(limit)

    result = await db.execute(stmt)
    # return  result.scalars().all()
    related_news = result.scalars().all()
    return [
        {
            "id": news.id,
            "title": news.title,
            "description": news.description,
            "content": news.content,
            "image": news.image,
            "author": news.author,
            "publish_time": news.publish_time,
            "categoryId": news.category_id,
            "views": news.views
        }
        for news in related_news
    ]
