from fastapi import APIRouter, Depends, status, HTTPException
from app.schemas import Review as ReviewSchema, ReviewCreate

from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db

from app.queries.selector import check_active_product

from app.auth import get_current_role

from app.services.reviews import get_avg_rating

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)

@router.get("/", response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """Получить все отзывы."""
    result = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )
    reviews = result.all()
    return reviews

@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
        review: ReviewCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_role("buyer"))
):
    """Добавление отзыва для товара, только для ролей buyer."""

    #Проверяем, что продукт существует и активен.
    product = await check_active_product(review.product_id, db)

    #Проверяем, оставлял ли текущий пользователь отзыв на данный товар
    already_use: ReviewModel | None = await db.scalar(
        select(ReviewModel)
        .where(ReviewModel.product_id == product.id,
               ReviewModel.user_id == current_user.id)
    )
    if already_use is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review already exist!")

    #Добавляем отзыв в БД.
    new_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(new_review)
    await db.flush()

    #Получаем среднее значение grade для продукта, после добавления отзыва
    product.rating = await get_avg_rating(product.id, db)

    await db.commit()
    await db.refresh(new_review)
    return new_review

@router.delete("/{review_id}", response_model=ReviewSchema)
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_role("buyer", "admin"))
):
    """Удаление отзыва по ID"""

    #Проверяем, что отзыв существует и активен
    review: ReviewModel | None = await db.scalar(
        select(ReviewModel)
        .where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    )
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or inactive!")

    #Если текущий пользователь с ролью buyer, проверяем, принадлежит ли ему этот отзыв
    if current_user.role == "buyer" and review.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user is not the author of the review!")

    #Удаляем отзыв(маркируем, как неактивный)
    review.is_active = False
    await db.flush()

    # Получаем среднее значение grade для продукта, после удаления отзыва
    product = await check_active_product(review.product_id, db)
    product.rating = await get_avg_rating(review.product_id, db)

    await db.commit()
    await db.refresh(review)
    return review