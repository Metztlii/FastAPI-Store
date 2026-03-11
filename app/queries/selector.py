from fastapi import HTTPException, status

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def check_active_category(category_id: int, category_db: AsyncSession, status_code: status = status.HTTP_400_BAD_REQUEST) -> CategoryModel:
    """Проверка существования категории."""
    stmt = select(CategoryModel).where(
        CategoryModel.id == category_id,
        CategoryModel.is_active == True
    )
    category: CategoryModel | None= await category_db.scalar(stmt)
    if category is None:
        raise HTTPException(status_code=status_code, detail='Category not found or inactive!')
    return category

async def check_active_product(product_id: int, product_db: AsyncSession, status_code: status = status.HTTP_404_NOT_FOUND) -> ProductModel:
    """Проверка существования товара."""
    stmt = select(ProductModel).where(
        ProductModel.id == product_id,
        ProductModel.is_active == True
    )
    product: ProductModel | None = await product_db.scalar(stmt)
    if product is None:
        raise HTTPException(status_code=status_code, detail='Product not found or inactive!')
    return product