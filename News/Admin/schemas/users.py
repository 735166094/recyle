from typing import Optional

from Crypto.SelfTest.Hash.test_cSHAKE import descr
from pydantic import BaseModel, ConfigDict, Field
from scripts.regsetup import description


class UserRequest(BaseModel):
    """
    用户注册/登录请求模型

    用于接收客户端传递的用户名和密码（明文），服务端后续会进行密码加密处理。
    """
    username: str  # 用户名，必填
    password: str  # 密码（明文），必填


class UserInfoBase(BaseModel):
    """
    用户信息基础模型（可更新字段）

    作为用户个人资料的可选更新字段模型，所有字段均为可选，更新时按需传入。
    """
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别（如 male/female/other）")
    bio: Optional[str] = Field(None, max_length=255, description="个人简介")


class UserInfoResponse(UserInfoBase):
    """
    用户信息响应模型（包含 ID 和用户名）

    继承自 UserInfoBase，并增加了用户的唯一标识和用户名，用于登录后返回或详情展示。
    同时配置了 from_attributes=True，支持从 ORM 对象自动转换。
    """
    id: int  # 用户唯一 ID
    username: str  # 用户名（不可更改）

    model_config = ConfigDict(
        from_attributes=True  # 支持从 SQLAlchemy 模型实例自动映射
    )


class UserAuthResponse(BaseModel):
    """
    用户认证响应模型（登录/注册成功后返回）

    包含访问令牌（token）和用户详细信息，前端可从中获取 token 并保存，用于后续接口鉴权。
    字段 user_info 在 JSON 中序列化为 "userInfo"，支持通过别名填充。
    """
    token: str  # JWT 访问令牌
    user_info: UserInfoResponse = Field(..., alias="userInfo")  # 用户信息，序列化时键名为 userInfo

    model_config = ConfigDict(
        populate_by_name=True,  # 允许通过字段名或别名进行赋值
        from_attributes=True  # 支持从 ORM 对象转换
    )
