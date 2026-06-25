from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import favorite
from models import news
from models.users import User
from schemas.favorite import FavoriteCheckResponse, FavoriteAddResponse, FavoriteListResponse
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/favorite", tags=["favorite"])


@router.get("/check")
async def check_favorite(
        news_id: int = Query(..., alias="newsId"),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    检查当前登录用户是否已收藏指定新闻。

    该接口用于前端在新闻详情页展示收藏按钮的初始状态（已收藏/未收藏）。

    Args:
        news_id: 新闻 ID，通过查询参数 newsId 传入（必填）。
        user: 当前登录用户对象，由 get_current_user 依赖注入（自动校验令牌）。
        db: 异步数据库会话，由依赖注入提供。

    Returns:
        统一响应格式，data 中包含：
            - is_favorited: bool，True 表示已收藏，False 表示未收藏。

    Raises:
        HTTPException:
            - 401 Unauthorized: 由 get_current_user 抛出，当令牌无效或过期时。
            - 500 Internal Server Error: 数据库操作失败时可能抛出（由全局异常处理器捕获）。
    """
    is_favorited = await favorite.is_news_favorited(db, user.id, news_id)
    return success_response(message="查询成功", data=FavoriteCheckResponse(is_favorited=is_favorited))


@router.post("/add")
async def add_favorite(
        data: FavoriteAddResponse,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    添加新闻收藏（当前登录用户收藏指定新闻）。

    该接口会在收藏表中插入一条记录，若已存在相同记录（同一用户+同一新闻），
    数据库唯一约束会抛出 IntegrityError，由全局异常处理器转换为统一响应。

    Args:
        data: 包含 news_id 的请求体（当前使用的模型为 FavoriteAddResponse，但建议使用请求模型）。
        user: 当前登录用户对象，由 get_current_user 依赖注入。
        db: 异步数据库会话，由依赖注入提供。

    Returns:
        统一响应格式，data 中包含新创建的收藏记录对象（Favorite ORM 模型序列化后的数据）。

    Raises:
        HTTPException:
            - 400 Bad Request: 当重复收藏时，由全局 IntegrityError 处理器转换为 "数据约束冲突"。
            - 401 Unauthorized: 由 get_current_user 抛出，令牌无效时。
            - 500 Internal Server Error: 其他数据库错误。

    Note:
        此处 data 参数类型为 FavoriteAddResponse，但通常请求体应使用请求模型（如 FavoriteAddRequest），
        否则可能导致字段名不匹配。建议后续优化时统一命名规范。
    """
    result = await favorite.add_news_favorite(db, user.id, data.news_id)
    return success_response(message="收藏成功", data=result)


@router.post("/remove")
async def remove_favorite(
        news_id: int = Query(..., alias="newsId"),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    取消新闻收藏（当前登录用户取消对指定新闻的收藏）。

    该接口会删除收藏表中对应的记录，若记录不存在则返回错误。

    Args:
        news_id: 新闻 ID，通过查询参数 newsId 传入（必填）。
        user: 当前登录用户对象，由 get_current_user 依赖注入。
        db: 异步数据库会话，由依赖注入提供。

    Returns:
        统一响应格式，message 为 "取消收藏成功"，data 为 None。

    Raises:
        HTTPException:
            - 400 Bad Request: 当取消收藏的记录不存在时（即该用户未收藏此新闻），detail 为 "取消收藏失败，记录不存在"。
            - 401 Unauthorized: 由 get_current_user 抛出，令牌无效时。
            - 500 Internal Server Error: 数据库操作失败时可能抛出。
    """
    result = await favorite.remove_news_favorite(db, user.id, news_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="取消收藏失败，记录不存在")
    return success_response(message="取消收藏成功")


@router.get("/list")
async def get_favorite_list(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的收藏列表（分页）。

    该接口返回用户收藏的所有新闻的简要信息，包括新闻ID、标题、描述、封面图、收藏时间等。
    结果按收藏时间倒序排列，并支持分页。

    Args:
        page: 当前页码，从 1 开始，默认为 1，最小值为 1。
        page_size: 每页记录数，默认为 10，取值范围为 1 ~ 100。
        user: 当前登录用户对象（由 get_current_user 依赖注入，已通过令牌认证）。
        db: 异步数据库会话（由 get_db 依赖注入）。

    Returns:
        统一响应格式，data 中包含：
            - list: 当前页的收藏列表（字典数组），每个元素包含：
                - news_id: 新闻ID
                - title: 新闻标题
                - description: 新闻简介
                - image: 封面图URL
                - favorite_time: 收藏时间（datetime）
                - favorite_id: 收藏记录主键ID
            - total: 用户总收藏数
            - hasMore: bool，是否还有下一页（用于前端“加载更多”判断）

    Raises:
        HTTPException:
            - 401 Unauthorized: 由 get_current_user 抛出，当访问令牌无效或过期时。
            - 500 Internal Server Error: 数据库操作失败时可能抛出（由全局异常处理器捕获）。
    """
    # 调用 CRUD 层获取分页数据（返回 items 列表和总数）
    items, total = await favorite.get_favorite_list(db, user.id, page, page_size)

    # 判断是否还有更多数据（当前页数 * 页大小 < 总数）
    has_more = total > page * page_size

    # 构造响应数据，FavoriteListResponse 会自动处理别名（list -> list, hasMore -> has_more）
    data = FavoriteListResponse(list=items, total=total, hasMore=has_more)
    return success_response(message="查询成功", data=data)


@router.post("/clear")
async def clear_favorite(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    清空当前登录用户的所有新闻收藏记录。

    该操作会永久删除该用户在收藏表中的所有记录，删除后不可恢复，请谨慎使用。
    通常用于用户主动清理收藏列表，或在账户注销时清理数据。

    Args:
        user: 当前登录用户对象，由 get_current_user 依赖注入（已通过令牌认证）。
        db: 异步数据库会话，由依赖注入提供。

    Returns:
        统一响应格式，message 中会动态包含成功删除的记录条数，
        例如 "已成功清空5条数据。"，data 字段为 None。

    Raises:
        HTTPException:
            - 401 Unauthorized: 由 get_current_user 抛出，当访问令牌无效或已过期时。
            - 500 Internal Server Error: 数据库操作失败时可能抛出（由全局异常处理器统一捕获）。
    """
    num = await favorite.clear_all_favorite(db, user.id)
    return success_response(message=f"已成功清空{num}条数据。")
