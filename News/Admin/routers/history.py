from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import favorite
from models.users import User
from schemas.favorite import FavoriteAddResponse
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/add")
async def add_history(
        data: FavoriteAddResponse,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    添加一条浏览历史记录（当前用户访问某篇新闻时调用）。

    该接口用于记录用户的浏览行为，便于后续展示历史列表。如果同一用户对同一新闻重复浏览，
    通常建议更新访问时间或仅保留最新记录，具体行为取决于 `favorite.all_news_history` 的实现。

    Args:
        data: 请求体，包含 newsId 字段（新闻 ID），使用 FavoriteAddResponse 模型。
        user: 当前登录用户对象（由 get_current_user 依赖注入）。
        db: 异步数据库会话（由 get_db 注入）。

    Returns:
        统一响应格式，data 中包含新创建或更新的历史记录对象（由 ORM 转换的字典）。

    Raises:
        HTTPException:
            - 401 Unauthorized: 令牌无效或过期（由 get_current_user 抛出）。
            - 500 Internal Server Error: 数据库操作失败。

    Note:
        此处调用的 `favorite.all_news_history` 命名可能具有误导性，
        似乎应是 `add_news_history` 或类似名称，请确认其实际功能。
    """
    # 注意：函数名 all_news_history 可能为笔误，可能是 add_news_history
    history = await favorite.all_news_history(db, user.id, data.news_id)
    return success_response(message="添加成功", data=history)


@router.get("/list")
async def get_history_list(
        page: int = 1,
        page_size: int = 10,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    分页获取当前用户的浏览历史记录。

    历史记录按浏览时间倒序排列（由 CRUD 函数内部实现），返回新闻基本信息及浏览时间。

    Args:
        page: 当前页码，从 1 开始，默认为 1（建议增加 ge=1 约束）。
        page_size: 每页记录数，默认为 10（建议增加 ge=1, le=100 约束）。
        user: 当前登录用户对象（由 get_current_user 依赖注入）。
        db: 异步数据库会话（由 get_db 注入）。

    Returns:
        统一响应格式，data 中包含：
            - list: 当前页的历史记录列表（字典数组，包含新闻详情和浏览时间）。
            - total: 总历史记录数。

    Raises:
        HTTPException:
            - 401 Unauthorized: 令牌无效或过期。
            - 500 Internal Server Error: 数据库操作失败。

    Note:
        分页参数未添加数值校验，建议添加 `Query(1, ge=1)` 和 `Query(10, ge=1, le=100)`。
    """
    history_list, total = await favorite.get_history_list(db, user.id, page, page_size)
    return success_response(message="获取成功", data={"list": history_list, "total": total})


@router.delete("/remove")
async def remove_history(
        user: User = Depends(get_current_user),
        news_id: int = Query(..., alias="newsId"),
        db: AsyncSession = Depends(get_db)
):
    """
    删除当前用户对指定新闻的浏览历史记录（单条删除）。

    Args:
        user: 当前登录用户对象（由 get_current_user 依赖注入）。
        news_id: 要删除的新闻 ID，通过查询参数 newsId 传入（必填）。
        db: 异步数据库会话（由 get_db 注入）。

    Returns:
        统一响应格式，message 为 "清空成功"，data 为 None。

    Raises:
        HTTPException:
            - 400 Bad Request: 如果记录不存在，可能会由 CRUD 函数抛出（需检查实现）。
            - 401 Unauthorized: 令牌无效或过期。
            - 500 Internal Server Error: 数据库操作失败。

    Note:
        此外，该接口使用 DELETE 方法，符合 RESTful 语义。
    """
    await favorite.clear_history(db, user.id, news_id)
    return success_response(message="清空成功")


@router.delete("/clear_all")
async def clear_all_history(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    清空当前用户的所有浏览历史记录（全部删除）。

    该操作会删除该用户历史表中的所有记录，一旦执行不可恢复，请谨慎使用。

    Args:
        user: 当前登录用户对象（由 get_current_user 依赖注入）。
        db: 异步数据库会话（由 get_db 注入）。

    Returns:
        统一响应格式，message 为 "清空成功"，data 为 None。

    Raises:
        HTTPException:
            - 401 Unauthorized: 令牌无效或过期。
            - 500 Internal Server Error: 数据库操作失败。

    Note:
        此接口与 `/remove` 区分，前者删除单条，后者删除全部。
    """
    await favorite.clear_all_history(db, user.id)
    return success_response(message="清空成功")
