from datetime import datetime

from sqlalchemy import UniqueConstraint, Index, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class History(Base):
    __tablename__ = "history"

    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),
        Index("fk_favorite_user_idx", "user_id"),
        Index("fk_favorite_news_idx", "news_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="历史ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news.id"), comment="新闻ID")
    created_at: Mapped[int] = mapped_column(Integer, default=datetime.now().timestamp(), nullable=False,
                                            comment="创建时间")

    def __repr__(self):
        return f"<Favorite(id={self.id}, user_id={self.user_id}, news_id={self.news_id})>"
