from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class HistoryAddResponse(BaseModel):
    """
    添加历史记录请求模型（用于接收前端传递的新闻ID）。

    注意：虽然命名为 Response，但实际用于请求体，建议改为 HistoryAddRequest 以避免混淆。
    """
    news_id: int = Field(
        ...,
        alias="newsId",
        description="要添加的历史记录新闻唯一标识 ID，前端通过 newsId 字段传递"
    )


class HistoryNewsItemResponse(HistoryAddResponse):
    """
    历史新闻列表项响应模型。

    继承自 NewsItemBase，用于返回历史新闻列表项的响应数据。
    """
    history_id: int = Field(alias="historyId")
    history_time: datetime = Field(alias="historyTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class HistoryListResponse(BaseModel):
    """
    历史新闻列表响应模型。

    用于返回历史新闻列表的响应数据。
    """
    list: list[HistoryNewsItemResponse]
    total: int
    has_moreL: bool = Field(alias="hasMore")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
