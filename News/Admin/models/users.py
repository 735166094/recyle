from datetime import datetime
from typing import Optional

from cytoolz import unique
from pydantic import BaseModel, Field
from pymongo.common import alias
from sqlalchemy import Index, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.testing.schema import mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """
    用户信息表ORM模型
    """
    __tablename__ = "user"

    __table_args__ = (
        Index('fk_user_username_idx', 'username'),
        Index('fk_user_phone', 'phone')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="昵称")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=False, comment="头像", default="")
    gender: Mapped[Optional[str]] = mapped_column(Enum("male", "female", "unknown"), nullable=False, comment="性别",
                                                  default="unknown")
    bio: Mapped[Optional[str]] = mapped_column(String(255), nullable=False, comment="简介", default="")
    phone: Mapped[Optional[str]] = mapped_column(String(11), nullable=False, comment="手机号", default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="创建时间", default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="更新时间", default=datetime.now)


class UserToken(Base):
    """
    用户令牌ORM模型
    """

    __tablename__ = "user_token"

    __table_args__ = (
        Index('token_UNIQUE', 'token'),
        Index('fk_user_token_user_id', 'user_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户令牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(255), nullable=False, comment="令牌")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="令牌过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="创建时间", default=datetime.now)

    def __repr__(self):
        """"""
        return f"<UserToken(id={self.id}, user_id={self.user_id}, token={self.token})>"


class UserUpdateRequest(BaseModel):
    """
    用户更新请求模型
    """

    nickname: str = Field(..., description="昵称")
    avatar: Optional[str] = Field(default="", description="头像")
    gender: Optional[str] = Field(default="unknown", description="性别")
    bio: Optional[str] = Field(default="", description="简介")
    phone: Optional[str] = Field(default="", description="手机号")


class UserChangePasswordRequest(BaseModel):
    """
    用户修改密码请求模型
    """
    old_password: str = Field(..., alias="oldPassword", description="旧密码")
    new_password: str = Field(..., alias="newPassword", description="新密码")
