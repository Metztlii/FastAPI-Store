from fastapi import APIRouter, Depends, status, HTTPException

from app.dependencies import get_async_db

from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel

from app.schemas import Product as ProductSchema, ProductCreate
from app.schemas import Review as ReviewSchema

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.queries.selector import check_active_product, check_active_category

from app.auth import get_current_role

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    result = await db.scalars(
        select(ProductModel).where(ProductModel.is_active == True)
    )
    return result.all()


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_role("seller"))
):
    """
    Создаёт новый товар, привязанный к текущему продавцу(Только для ролей 'seller').
    """
    await check_active_category(product.category_id, db)
    new_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    await check_active_category(category_id, db)
    stmt = select(ProductModel).where(
        ProductModel.category_id == category_id,
        ProductModel.is_active == True
    )
    return (await db.scalars(stmt)).all()


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product = await check_active_product(product_id, db)
    await check_active_category(product.category_id, db)
    return product

@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
        product_id: int,
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_role("seller"))
):
    """
    Обновляет товар по его ID.
    """
    updated_product: ProductModel | None = await check_active_product(product_id, db)
    if updated_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only update your own products')
    await check_active_category(product.category_id, db)
    for key, value in product.model_dump().items():
        setattr(updated_product, key, value)
    await db.commit()
    await db.refresh(updated_product)
    return updated_product


@router.delete("/{product_id}", response_model=ProductSchema)
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_role("seller"))
):
    """
    Удаляет товар по его ID.
    """
    product = await check_active_product(product_id, db)
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You can only delete your own products'
        )
    product.is_active = False
    await db.commit()
    await db.refresh(product)
    return product

@router.get("/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_product_reviews(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получить все отзывы по продукту."""
    await check_active_product(product_id, db)
    results = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.is_active == True)
    )
    reviews = results.all()
    return reviews