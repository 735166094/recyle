from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from schemas.base import NewsItemBase


class FavoriteCheckResponse(BaseModel):
    """
    收藏状态检查响应模型。

    用于返回当前用户是否已收藏某篇新闻的结果。
    """
    is_favorite: bool = Field(
        ...,
        alias="is_favorite",
        description="是否已收藏，True 表示已收藏，False 表示未收藏"
    )


class FavoriteAddResponse(BaseModel):
    """
    添加收藏请求模型（用于接收前端传递的新闻ID）。

    注意：虽然命名为 Response，但实际用于请求体，建议改为 FavoriteAddRequest 以避免混淆。
    """
    news_id: int = Field(
        ...,
        alias="newsId",
        description="要收藏的新闻唯一标识 ID，前端通过 newsId 字段传递"
    )


class FavoriteNewsItemResponse(NewsItemBase):
    """
    收藏新闻列表项响应模型。

    继承自 NewsItemBase，用于返回收藏新闻列表项的响应数据。
    """
    favorite_id: int = Field(alias="favoriteId")
    favorite_time: datetime = Field(alias="favoriteTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class FavoriteListResponse(BaseModel):
    """
    收藏新闻列表响应模型。

    用于返回收藏新闻列表的响应数据。
    """
    list: list[FavoriteNewsItemResponse]
    total: int
    has_moreL: bool = Field(alias="hasMore")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
