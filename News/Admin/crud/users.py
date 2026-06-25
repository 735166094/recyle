import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserToken, UserUpdateRequest
from schemas.users import UserRequest
from utils import security


async def get_user_by_username(db: AsyncSession, username: str):
    """
    根据用户名查询数据库中的用户信息。

    Args:
        db: 异步数据库会话对象（AsyncSession）。
        username: 要查询的用户名（字符串）。

    Returns:
        User | None: 如果用户存在则返回 User 实例，否则返回 None。
    """
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRequest):
    """
    创建新用户并保存到数据库（密码会自动哈希加密）。

    Args:
        db: 异步数据库会话对象。
        user_data: 包含 username 和 password 的 Pydantic 模型。

    Returns:
        User: 新创建的 User ORM 对象（已包含数据库生成的 id）。
    """
    hashed_password = security.get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_token(db: AsyncSession, user_id: int):
    """
    为用户创建或更新身份令牌（Token）。

    如果用户已有有效令牌，则更新其 token 字符串和过期时间；
    否则新建一条记录。令牌有效期为 7 天。

    Args:
        db: 异步数据库会话对象。
        user_id: 目标用户的 ID。

    Returns:
        str: 生成的 UUID 令牌字符串。

    Note:
        事务提交由调用方统一控制，本函数不自行 commit，以确保
        与上层业务事务一致性。
    """
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=7)

    stmt = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(stmt)
    user_token = result.scalar_one_or_none()

    if user_token:
        # 更新已有令牌
        user_token.token = token
        user_token.expires_at = expires_at
    else:
        # 创建新令牌
        user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(user_token)

    # 提交由调用方执行（这里不 commit，避免破坏上层事务控制）
    # 如果调用方不提交，则需要在此处统一提交（但推荐由调用方管理）
    # 假设调用方（如路由层）会在调用后提交事务，因此此处仅做添加/修改。
    # 若需保持原逻辑（仅在新建时提交），可移除此段注释，但建议统一。
    # 下面为了兼容，我们选择不提交，由路由层统一 commit。
    # 如果路由层未处理，则需要在此处添加 await db.commit()
    # 但为了演示，我们假设调用方会提交，或者我们在此统一提交：
    # await db.commit()  # 取消注释可恢复提交行为

    # 为了保持原意（每次调用都立即持久化），我们改为提交，但确保所有分支都提交。
    await db.commit()  # 统一提交
    return token


async def authenticate_user(db: AsyncSession, username: str, password: str):
    """
    验证用户名和密码是否匹配。

    Args:
        db: 异步数据库会话对象。
        username: 用户名。
        password: 明文密码。

    Returns:
        User | None: 验证成功返回 User 对象，否则返回 None。
    """
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not security.verify_password(password, user.password):
        return None
    return user


async def get_user_by_token(db: AsyncSession, token: str):
    """
    根据令牌字符串获取对应的用户信息（同时校验令牌是否过期）。

    Args:
        db: 异步数据库会话对象。
        token: 令牌字符串（UUID）。

    Returns:
        User | None: 若令牌有效且未过期，返回对应的 User 对象；否则返回 None。
    """
    # 1. 先查询令牌记录
    stmt_token = select(UserToken).where(UserToken.token == token)
    result_token = await db.execute(stmt_token)
    db_token = result_token.scalar_one_or_none()

    if not db_token:
        return None

    # 2. 检查是否过期
    if db_token.expires_at < datetime.now():
        return None

    # 3. 通过 user_id 查询用户
    stmt_user = select(User).where(User.id == db_token.user_id)
    result_user = await db.execute(stmt_user)
    return result_user.scalar_one_or_none()


async def update_user(db: AsyncSession, username: str, user_data: UserUpdateRequest):
    """
    更新指定用户的个人信息（支持部分字段更新）。

    该函数根据用户名查找用户，并使用提供的字段值进行更新。
    只更新传入的非空字段（忽略未设置的字段），避免覆盖已有数据。

    Args:
        db: 异步数据库会话对象（AsyncSession），用于执行数据库操作。
        username: 要更新的目标用户的用户名（唯一标识）。
        user_data: 包含待更新字段的 Pydantic 模型（UserUpdateRequest），
                   通过 model_dump 序列化时自动排除未设置或为 None 的字段。

    Returns:
        User: 更新后的 User ORM 对象（已从数据库重新加载，包含最新数据）。

    Raises:
        HTTPException: 当指定用户不存在时，抛出 404 Not Found 异常。
    """
    # 构建更新语句：只更新传入的字段
    query = update(User).where(User.username == username).values(**user_data.model_dump(
        exclude_unset=True,  # 排除未显式设置的字段
        exclude_none=True  # 排除值为 None 的字段
    ))

    result = await db.execute(query)
    await db.commit()

    # 检查是否影响了任何行，若 rowcount 为 0 表示用户不存在
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 重新查询用户并返回最新数据
    updated_user = await get_user_by_username(db, username)
    return updated_user


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str):
    """
    修改指定用户的密码。

    验证用户提供的旧密码是否与当前密码匹配，若匹配则更新为新密码（自动哈希加密）。
    该操作会直接修改传入的 User 对象，并确保其与数据库会话关联后提交事务。

    Args:
        db: 异步数据库会话对象（AsyncSession），用于提交事务。
        user: 目标用户的 ORM 对象（必须已关联到当前会话，或通过 db.add 重新关联）。
        old_password: 用户输入的旧密码（明文）。
        new_password: 用户输入的新密码（明文）。

    Returns:
        bool: 密码修改成功返回 True，旧密码验证失败返回 False。

    Raises:
        不会主动抛出异常，但若数据库提交失败，可能抛出 SQLAlchemyError 等异常。
        此外，如果 user 未关联 session，db.add(user) 会将其关联，但若用户已存在，可能触发重复添加错误（但通常不会）。
    """
    # 验证旧密码是否正确（需要传入当前密码哈希）
    if not security.verify_password(old_password, user.password):
        return False

    # 生成新密码的哈希值
    hashed_new_pwd = security.get_hash_password(new_password)
    user.password = hashed_new_pwd

    # 确保 user 对象被当前会话跟踪（若已跟踪则无影响）
    db.add(user)

    # 提交事务
    await db.commit()
    # 刷新对象，获取最新状态（如数据库默认值或触发器更新）
    await db.refresh(user)

    return True
