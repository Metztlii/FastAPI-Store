from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.dependencies import get_async_db

from app.queries.selector import check_active_category


# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех категорий товаров.
    """
    result = await db.scalars(select(CategoryModel).where(CategoryModel.is_active == True))
    categories = result.all()
    return categories


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Создаёт новую категорию.
    """
    # Проверка существования parent_id, если указан
    if category.parent_id:
      await check_active_category(category.parent_id, db)
    # Создание новой категории
    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category



@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(
        category_id: int,
        category: CategoryCreate,
        db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID.
    """
    updated_category = await check_active_category(category_id, db, status_code=status.HTTP_404_NOT_FOUND)
    await check_active_category(category.parent_id, db)

    updated_category.name = category.name
    updated_category.parent_id = category.parent_id
    await db.commit()
    await db.refresh(updated_category)
    return updated_category


@router.delete("/{category_id}", response_model=CategorySchema, status_code=status.HTTP_200_OK)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
        Удаляет категорию по её ID.
    """
    category = await check_active_category(category_id, db, status_code=status.HTTP_404_NOT_FOUND)
    category.is_active = False
    await db.commit()
    return category