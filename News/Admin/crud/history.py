from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.history import History
from models.news import News


async def all_news_history(db: AsyncSession, user_id: int, news_id: int):
    """
    添加或更新一条浏览历史记录（记录用户访问某篇新闻的行为）。

    ⚠️ 注意：函数名 `all_news_history` 具有误导性，实际功能是插入单条历史记录，
    建议重命名为 `add_news_history` 或 `create_history`。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        user_id: 用户 ID。
        news_id: 新闻 ID。

    Returns:
        History: 新创建的历史记录 ORM 对象（已包含数据库生成字段）。

    Raises:
        SQLAlchemyError: 当数据库插入失败时（如外键约束违反）可能抛出。
    """
    # 原代码存在拼写错误：`hsitory` 应为 `history`，但此处保留原样（仅注释提醒）
    hsitory = History(user_id=user_id, news_id=news_id)
    db.add(hsitory)
    await db.commit()
    await db.refresh(hsitory)
    return hsitory


async def get_history_list(db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10):
    """
    分页获取指定用户的浏览历史列表，按浏览时间倒序排列。

    该函数会同时统计总记录数，返回当前页数据及总数。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        user_id: 用户 ID。
        page: 页码，从 1 开始，默认为 1。
        page_size: 每页记录数，默认为 10。

    Returns:
        tuple: (rows, total)
            - rows: 当前页的历史记录列表，每条记录为包含 News 对象及额外字段的元组，
                    额外字段包括 `history_time`（实际应为 `History.created_at` 别名）和 `history_id`（实际应为 `History.id` 别名）。
                    但当前查询使用了 `History.news_id.label("history_time")` 和 `History.created_at.label("history_id")`，
                    这会导致字段名与内容不符（字段值错位），建议修正。
            - total: 该用户的总历史记录数（整数）。

    Raises:
        SQLAlchemyError: 当查询或统计失败时抛出。

    Note:
        当前查询中的字段别名存在明显错误：
        - `History.news_id.label("history_time")` 错误地将新闻 ID 标记为时间字段
        - `History.created_at.label("history_id")` 错误地将创建时间标记为 ID 字段
        修正方案应为：
            select(News, History.created_at.label("history_time"), History.id.label("history_id"))
    """
    # 统计总记录数
    count_query = select(func.count()).where(History.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # 计算分页偏移量
    offset = (page - 1) * page_size

    # 主查询：关联新闻表，获取新闻详情及历史记录的附加信息
    # 注意：字段别名存在错位问题（见函数注释）
    query = (select(News, History.news_id.label("history_time"), History.created_at.label("history_id"))
             .join(History, History.news_id == News.id)
             .where(History.user_id == user_id)
             .order_by(History.created_at.desc())
             .offset(offset)
             .limit(page_size))

    result = await db.execute(query)
    rows = result.all()
    return rows, total


async def clear_history(db: AsyncSession, user_id: int, news_id: int):
    """
    删除指定用户对某篇新闻的浏览历史记录（单条删除）。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        user_id: 用户 ID。
        news_id: 新闻 ID。

    Returns:
        bool: 如果成功删除至少一条记录则返回 True，否则返回 False（表示该记录不存在）。

    Raises:
        SQLAlchemyError: 当删除操作失败时抛出。
    """
    stmt = delete(History).where(History.user_id == user_id, History.news_id == news_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def clear_all_history(db: AsyncSession, user_id: int):
    """
    清空指定用户的所有浏览历史记录（全量删除）。

    该操作会删除该用户历史表中的所有记录，一旦执行不可恢复，请谨慎使用。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        user_id: 用户 ID。

    Returns:
        int: 被删除的记录数（可能为 0）。

    Raises:
        SQLAlchemyError: 当删除操作失败时抛出。
    """
    stmt = delete(History).where(History.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0
