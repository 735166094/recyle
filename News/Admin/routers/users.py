from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import users
from crud.users import get_user_by_username, create_user
from models.users import User, UserUpdateRequest, UserChangePasswordRequest
from schemas.users import UserRequest, UserAuthResponse, UserInfoResponse
from utils.auth import get_current_user
from utils.logger import get_logger
from utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register")
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    """
    用户注册接口

    接收用户名和明文密码，校验用户名唯一性，创建新用户并生成 JWT 访问令牌。
    密码会在 create_user 内部自动加密存储。

    :param user_data: 包含 username 和 password 的请求体（UserRequest 模型）
    :param db: 异步数据库会话，由依赖注入提供
    :return: 统一响应格式，data 中包含：
             - token: JWT 访问令牌（用于后续鉴权）
             - user_info: 用户详细信息（id、username、nickname、avatar、gender、bio）
    :raises HTTPException: 当用户名已存在时，返回 400 Bad Request
    """
    logger.info("用户注册尝试: %s", user_data.username)
    existing_user = await get_user_by_username(db, user_data.username)
    if existing_user:
        logger.warning("用户名已存在: %s", user_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    user = await create_user(db, user_data)
    token = await user.create_token(db, user.id)
    # 以下为旧版返回逻辑，已注释，统一使用 success_response 和 Pydantic 模型
    # return {
    #     "code": 200,
    #     "message": "success",
    #     "data": {
    #         "token": token,
    #         "id": user.id,
    #         "username": user.username,
    #         "bio": user.bio,
    #         "avatar": user.avatar
    #     }
    # }
    response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    logger.info("用户注册成功: %s", user.username)
    return success_response(message="注册成功", data=response_data)


@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    """
    用户登录接口

    校验用户名和密码（明文），验证通过后生成 JWT 访问令牌并返回用户信息。

    :param user_data: 包含 username 和 password 的请求体（UserRequest 模型）
    :param db: 异步数据库会话，由依赖注入提供
    :return: 统一响应格式，data 中包含：
             - token: JWT 访问令牌
             - user_info: 用户详细信息（id、username、nickname、avatar、gender、bio）
    :raises HTTPException: 当用户名或密码错误时，返回 401 Unauthorized
    """

    logger.info("用户登录尝试: %s", user_data.username)

    user = await users.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        logger.warning("用户登录失败，用户名: %s", user_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = await user.create_token(db, user.id)
    response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    logger.info("用户登录成功: %s", user.username)
    return success_response(message="登录成功", data=response_data)


@router.get("/info")
async def get_user_info(user: User = Depends(get_current_user)):
    """
    获取当前用户信息接口

    返回当前用户详细信息（id、username、nickname、avatar、gender、bio）。

    :param user: 当前用户对象，由 get_current_user 函数提供
    :return: 统一响应格式，data 中包含用户详细信息
    """
    # logger.info("获取用户信息: %s", user.username)
    response_data = UserInfoResponse.model_validate(user)
    # logger.info("获取用户信息成功: %s", user.username)
    return success_response(message="获取用户信息成功", data=response_data)


@router.put("/update")
async def update_user_info(user_data: UserUpdateRequest, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    """
    更新当前用户信息接口

    接收用户名和昵称，更新当前用户信息。

    :param user_data: 待更新的用户信息（UserUpdateRequest 模型）
    :param user: 当前用户对象，由 get_current_user 函数提供
    :param db: 异步数据库会话，由依赖注入提供
    :return: 统一响应格式，data 中包含更新后的用户详细信息
    """
    user = await users.update_user(db, user.username, user_data)
    response_data = UserInfoResponse.model_validate(user)
    return success_response(message="用户信息更新成功", data=response_data)


@router.put("/password")
async def update_user_password(password_data: UserChangePasswordRequest, user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    """
    修改当前登录用户的密码。

    该接口要求用户提供旧密码和新密码，验证旧密码正确后更新为新密码。
    新密码会在服务端进行哈希加密后存储，确保安全性。

    Args:
        password_data: 包含旧密码和新密码的请求体（UserChangePasswordRequest 模型）。
        user: 当前登录用户对象，由 get_current_user 依赖注入（自动校验令牌）。
        db: 异步数据库会话，由依赖注入提供。

    Returns:
        统一响应格式，message 为 "密码更新成功"，data 为 None。

    Raises:
        HTTPException:
            - 400 Bad Request: 当旧密码验证失败时抛出，detail 为 "旧密码错误"。
            - 401 Unauthorized: 由 get_current_user 依赖抛出，当令牌无效或过期时。
            - 500 Internal Server Error: 数据库操作失败时可能抛出（由上层异常处理器捕获）。
    """
    res_change_pwd = await users.change_password(db, user, password_data.old_password, password_data.new_password)
    if not res_change_pwd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")
    return success_response(message="密码更新成功")
