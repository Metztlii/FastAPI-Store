from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel

async def get_avg_rating(product_id: int, db: AsyncSession):
    avg_product_rating = await db.scalar(
            select(func.avg(ReviewModel.grade))
            .where(ReviewModel.product_id == product_id,
                   ReviewModel.is_active == True)
        )
    return avg_product_rating or 0.00