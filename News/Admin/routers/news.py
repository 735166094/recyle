from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import news, news_cache

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories")
async def get_categories(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    获取新闻分类列表（分页）

    :param skip: 分页偏移量，默认从第 0 条开始
    :param limit: 每页返回的最大记录数，默认 100
    :param db: 异步数据库会话，由依赖注入提供
    :return: 统一响应格式，data 字段为 Category 对象列表
    """
    categories = await news_cache.get_categories(db, skip, limit)
    return {
        "code": 200,
        "message": "success",
        "data": categories
    }


@router.get("/list")
async def get_news_list(
        category_id: int = Query(..., alias="categoryId"),
        page: int = 1,
        page_size: int = Query(10, alias="pageSize", le=100),
        db: AsyncSession = Depends(get_db)
):
    """
    根据分类 ID 分页查询新闻列表

    :param category_id: 新闻分类 ID（必填），通过查询参数 `categoryId` 传入
    :param page: 当前页码，从 1 开始，默认 1
    :param page_size: 每页条数，默认 10，最大 100（通过 `pageSize` 传入）
    :param db: 异步数据库会话，由依赖注入提供
    :return: 统一响应格式，data 包含：
             - list: 当前页的新闻列表（News 对象）
             - total: 该分类下的新闻总数
             - hasMore: 是否还有更多数据（用于前端判断是否显示加载更多）
    """
    offset = (page - 1) * page_size
    news_list = await news_cache.get_news_list(db, category_id, offset, page_size)
    total = await news.get_news_count(db, category_id)
    has_more = (offset + len(news_list)) < total

    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": news_list,
            "total": total,
            "hasMore": has_more
        }
    }


@router.get("/detail")
async def get_news_detail(news_id: int = Query(..., alias="id"), db: AsyncSession = Depends(get_db)):
    """
    获取新闻详情，同时自动增加一次浏览量，并返回同分类下的相关新闻（最多 3 条）

    :param news_id: 新闻 ID（必填），通过查询参数 `id` 传入
    :param db: 异步数据库会话，由依赖注入提供
    :return: 统一响应格式，data 包含：
             - id: 新闻 ID
             - title: 标题
             - description: 简介
             - content: 正文内容
             - image: 封面图片链接
             - author: 作者
             - views: 当前浏览量（已增加）
             - publishTime: 发布时间，格式化为 "YYYY-MM-DD HH:MM:SS"
             - categoryId: 所属分类 ID
             - relatedNews: 相关新闻列表（同分类，排除自身，按发布时间和浏览量降序）
    :raises HTTPException: 当新闻不存在时，返回 404 状态码
    """
    news_detail = await get_news_detail()  # ⚠️ 注意：此处存在同名函数递归调用，应修正为 `await news.get_news_detail(db, news_id)` 等

    if not news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")

    views_res = await news.increase_news_view(db, news_detail)
    if not views_res:
        raise HTTPException(status_code=404, detail="新闻不存在")

    related_news = await news.get_related_news(db, news_id, news_detail.category_id)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": news_detail.id,
            "title": news_detail.title,
            "description": news_detail.description,
            "content": news_detail.content,
            "image": news_detail.image,
            "author": news_detail.author,
            "views": news_detail.views,
            "publishTime": news_detail.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
            "categoryId": news_detail.category_id,
            "relatedNews": related_news
        }
    }
