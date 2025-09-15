from datetime import datetime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, Text

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    # For v1 keep it simple: comma-separated categories
    categories: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    players_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    players_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    playtime_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    playtime_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
