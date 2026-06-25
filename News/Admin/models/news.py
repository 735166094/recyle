from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Index, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(),
        comment="创建时间",
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(),
        onupdate=datetime.now(),
        comment="更新时间",
        nullable=False
    )


class Category(Base):
    __tablename__ = "news_category"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")


class News(Base):
    __tablename__ = "news"

    # 索引
    __table_args__ = (
        Index('fk_news_category_idx', 'category_id'),
        Index('fk_publish_time', 'publish_time')
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="新闻简介")
    content: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻内容")
    image: Mapped[Optional[str]] = mapped_column(String(255), comment="新闻图片")
    author: Mapped[Optional[str]] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_category.id"), nullable=False, comment="分类ID")
    views: Mapped[int] = mapped_column(Integer, default=0, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="发布时间")

    def __repr__(self):
        """
        __repr__方法的作用：返回对象的官方字符串表示，用于开发者调试
        :return:
        """
        return f"<News(id={self.id}, title={self.title}, views={self.views})>"
