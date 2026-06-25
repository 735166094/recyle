from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models.favorite import Favorite
from models.news import News
from utils.logger import setup_logging

logger = setup_logging()

async def is_news_favorited(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """
    判断指定用户是否收藏了某篇新闻。

    :param db: 异步数据库会话对象（AsyncSession），用于执行查询。
    :param user_id: 目标用户的唯一标识 ID。
    :param news_id: 目标新闻的唯一标识 ID。
    :return: 若该用户已收藏该新闻则返回 True，否则返回 False。
    :raises SQLAlchemyError: 当数据库查询出错时可能抛出（如连接超时、语法错误等）。
    """
    query = select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def add_news_favorite(db: AsyncSession, user_id: int, news_id: int) -> Favorite:
    """
    添加一条新闻收藏记录（用户收藏新闻）。

    该操作会在收藏表中插入一条新记录，并在提交事务后刷新对象以获取数据库生成的字段（如自增主键）。

    :param db: 异步数据库会话对象（AsyncSession）。
    :param user_id: 执行收藏操作的用户 ID。
    :param news_id: 被收藏的新闻 ID。
    :return: 新创建的 Favorite ORM 对象（包含数据库生成的所有字段）。
    :raises IntegrityError: 如果同一用户对同一新闻重复收藏（违反唯一约束）或外键关联数据不存在时抛出。
    :raises SQLAlchemyError: 其他数据库操作错误时抛出。
    """
    favorite = Favorite(user_id=user_id, news_id=news_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    return favorite


async def remove_news_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """
    移除指定用户的某条新闻收藏记录。

    该操作会删除完全匹配的记录。如果记录不存在，则不会产生任何影响。

    :param db: 异步数据库会话对象（AsyncSession）。
    :param user_id: 用户的唯一标识 ID。
    :param news_id: 新闻的唯一标识 ID。
    :return: 如果成功删除至少一条记录（即原来存在该收藏）则返回 True，否则返回 False。
    :raises SQLAlchemyError: 当数据库操作失败时抛出（如连接错误、超时等）。
    """
    stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_favorite_list(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 10
):
    """
    获取指定用户的收藏列表。

    :param db: 异步数据库会话对象（AsyncSession）。
    :param user_id: 用户的 ID。
    :param page: 页码，默认为 1。
    :param page_size: 每页数量，默认为 10。
    :return: 收藏列表，包含新闻 ID 和新闻标题。
    :raises SQLAlchemyError: 当数据库操作失败时抛出（如连接错误、超时等）。
    """

    count_query = select(func.count()).where(Favorite.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    offset = (page - 1) * page_size
    query = (select(News, Favorite.news_id.label("favorite_time"), Favorite.created_at.label("favorite_id"))
             .join(Favorite, Favorite.news_id == News.id)
             .where(Favorite.user_id == user_id)
             .order_by(Favorite.created_at.desc())
             .offset(offset)
             .limit(page_size))
    # logger.debug(f"get_favorite_list query: {query}")

    result = await db.execute(query)
    rows = result.all()
    return rows, total


async def clear_all_favorite(db: AsyncSession, user_id: int):
    """
    清空指定用户的所有收藏记录。

    :param db: 异步数据库会话对象（AsyncSession）。
    :param user_id: 用户的 ID。
    :return: 无返回值。
    :raises SQLAlchemyError: 当数据库操作失败时抛出（如连接错误、超时等）。
    """
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount or 0
