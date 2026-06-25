from celery.bin.result import result
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.news import Category, News


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 10):
    """
    分页查询新闻种类

    :param db: 异步数据库会话对象（AsyncSession），用于执行 SQL 查询
    :param skip: 分页偏移量，表示跳过的记录条数，默认为 0（即从第一条开始）
    :param limit: 每页最多返回的记录条数，默认为 10
    :return: 包含查询到的 Category 对象的列表（List[Category]），若没有数据则返回空列表
    """
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_news_list(db: AsyncSession, category_id: int, skip: int = 0, limit: int = 10):
    """
    根据新闻分类ID分页查询新闻列表

    :param db: 异步数据库会话对象（AsyncSession），用于执行 SQL 查询
    :param category_id: 新闻分类的外键 ID，用于筛选指定类别的新闻
    :param skip: 分页偏移量，表示跳过的记录条数，默认为 0（从第一条开始）
    :param limit: 每页最多返回的记录条数，默认为 10
    :return: 包含查询到的 News 对象的列表（List[News]），若该类目下暂无新闻则返回空列表
    """
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


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
