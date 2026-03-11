from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.users import User as UserModel
from app.config import SECRET_KEY, ALGORITHM
from app.dependencies import get_async_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated='auto')

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

def hash_password(password: str) -> str:
    #Преобразует пароль в хэш.
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    #Проверяет, соответствует ли введённый пароль сохранённому хешу.
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    """Создает JWT с payload (sub, role, id, exp)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "token_type": "access",
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """Создает refresh токен с длительным сроком действия."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_async_db)):
    """Проверяет JWT и возвращает пользователя из базы."""
    def credentials_exception(content: str = "Could not validate credentials") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=content,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')
        if email is None:
            raise credentials_exception()
        if token_type != 'access':
            raise credentials_exception('Invalid token type')
    except jwt.ExpiredSignatureError:
        raise credentials_exception('Token has expired')
    except jwt.PyJWTError:
        raise credentials_exception()
    user: UserModel | None = await db.scalar(
        select(UserModel).where(UserModel.email == email, UserModel.is_active == True))
    if user is None:
        raise credentials_exception('User not found or inactive')
    return user

def get_current_role(*args):
    async def dependecy(current_user: UserModel = Depends(get_current_user)):
        """Проверяет, что пользователь имеет роль переданную в аргументе role."""
        print(current_user.role)
        print(args)
        if current_user.role not in args:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This action is not available for your role!",
            )
        return current_user
    return dependecy