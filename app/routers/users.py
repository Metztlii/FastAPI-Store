import jwt
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.config import SECRET_KEY, ALGORITHM
from app.schemas import User as UserSchema, UserCreate, RefreshTokenRequest
from app.dependencies import get_async_db

from app.models.users import User as UserModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, verify_password, create_access_token, create_refresh_token


router = APIRouter(
    prefix="/users",
    tags=["users"]
)


@router.post('/', response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Регистрирует нового пользователя с ролью 'buyer' или 'seller'."""
    result = await db.scalars(select(UserModel).where(UserModel.email == user.email))
    if result.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered!')
    db_user = UserModel(
        email=user.email,
        hashed_password=hash_password(user.password.get_secret_value()),
        role=user.role
    )
    db.add(db_user)
    await db.commit()
    return db_user

@router.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_async_db)):
    """Аутентифицирует пользователя и возвращает JWT с Email, role и id."""
    user: UserModel | None = await db.scalar(
        select(UserModel).where(
            UserModel.email == form_data.username,
            UserModel.is_active == True)
    )
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password!',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token = create_access_token(data={'sub': user.email, 'role': user.role, 'id': user.id})
    refresh_token = create_refresh_token(data={'sub': user.email, 'role': user.role, 'id': user.id})
    return {'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer'}

@router.post('/refresh-token')
async def refresh_token(body: RefreshTokenRequest,
                        db: AsyncSession = Depends(get_async_db)):
    """Обновляет refresh-токен, принимая старый refresh-токен в теле запроса"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate refresh-token',
        headers={'WWW-Authenticate': 'Bearer'}
    )
    old_refresh_token = body.refresh_token

    try:
        payload = jwt.decode(old_refresh_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')
        #Проверяем, что токен действительно refresh
        if email is None or token_type != 'refresh':
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        #Срок refresh-token истек
        raise credentials_exception
    except jwt.PyJWTError:
        #подпись неверна или токен поврежден
        raise credentials_exception

    #Проверяем, что пользователь существует и активен
    user: UserModel | None = await db.scalar(
        select(UserModel).where(UserModel.email == email, UserModel.is_active == True)
    )
    if user is None:
        raise HTTPException(status_code=404, detail='User not found or inactive!')

    #Генерируем новый refresh-token
    new_refresh_token = create_refresh_token(data={'sub': user.email, 'role': user.role, 'id': user.id})
    return {
        'refresh_token': new_refresh_token,
        'token_type': 'bearer',
    }

@router.post('/access-token')
async def access_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate refresh-token',
        headers={'WWW-Authenticate': 'Bearer'}
    )
    try:
        payload = jwt.decode(body.refresh_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')
        if email is None or token_type != 'refresh':
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user: UserModel | None = await db.scalar(
        select(UserModel).where(UserModel.email == email, UserModel.is_active == True)
    )
    if user is None:
        raise HTTPException(status_code=404, detail='User not found or inactive!')

    # Генерируем новый refresh-token
    new_access_token = create_access_token(data={'sub': user.email, 'role': user.role, 'id': user.id})
    return {
        'access_token': new_access_token,
        'token_type': 'bearer',
    }
