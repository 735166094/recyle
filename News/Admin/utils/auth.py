from curl_cffi.requests import AsyncSession  # ⚠️ 此处可能导入错误，通常应使用 sqlalchemy.ext.asyncio.AsyncSession
from fastapi import Header, Depends, HTTPException
from fastapi import status

from config.db_config import get_db
from crud.users import get_user_by_token


async def get_current_user(
        authorization: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_db)
):
    """
    从请求头中提取 Authorization 令牌并验证用户身份。

    该函数作为 FastAPI 依赖项，用于保护需要登录的接口。
    它会从请求头获取 Authorization 字段（不包含 "Bearer " 前缀，需纯令牌字符串），
    然后调用数据库查询验证令牌是否有效且未过期，并返回对应的用户对象。

    Args:
        authorization: 从请求头中自动提取的 Authorization 字段值（纯令牌字符串）。
        db: 异步数据库会话，由依赖注入提供。

    Returns:
        User: 通过令牌验证的 User ORM 对象。

    Raises:
        HTTPException: 当令牌无效或用户不存在时，抛出 401 Unauthorized 异常。
    """
    # 注意：此处直接将 authorization 作为 token 使用，但实际常见的 Authorization 头
    # 格式为 "Bearer <token>"，可能需要先去除 "Bearer " 前缀。当前实现假设传入的是纯令牌。
    token = authorization
    user = await get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    return user