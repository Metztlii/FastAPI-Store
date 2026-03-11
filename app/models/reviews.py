from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, DateTime, Integer, ForeignKey, Boolean, CheckConstraint
from datetime import datetime

from app.models.users import User
from app.models.products import Product

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    grade: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("grade BETWEEN 1 AND 5"), #Ограничение размера целочисленного значения в поле от 1 до 5
        nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    #Отношения с таблицами users и products
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")