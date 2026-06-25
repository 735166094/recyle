from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class NewsItemBase(BaseModel):
    """
    新闻项的基类，定义了新闻项的公共字段。
    """
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: Optional[datetime] = Field(None, aliias="publishedTime")

    model_config = ConfigDict(
        from_attributes=True,  # 支持从 SQLAlchemy 模型实例自动映射
        populate_by_name=True
    )
