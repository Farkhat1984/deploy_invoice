# app/core/config.py
from dotenv import load_dotenv
from functools import lru_cache
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_NAME: str
    DB_PORT: int

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Modified original file (auth.py)
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.core.config import  get_db
from app.models.models import User, Invoice
from app.schemas.schemas import TokenData
from fastapi import Depends

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


async def get_user_shop_data(session: AsyncSession, user: User) -> Dict[str, Any]:
    """Get user's shop ID and last invoice information"""
    query = select(User).options(
        joinedload(User.shops)
    ).where(User.id == user.id)

    result = await session.execute(query)
    user_with_shops = result.unique().scalar_one_or_none()

    if not user_with_shops or not user_with_shops.shops:
        return {
            "user_shop_id": None,
            "last_invoice_id": None
        }

    user_shop = user_with_shops.shops[0]

    invoice_query = select(Invoice).where(
        Invoice.user_id == user.id,
        Invoice.shop_id == user_shop.id
    ).order_by(Invoice.created_at.desc()).limit(1)

    invoice_result = await session.execute(invoice_query)
    last_invoice = invoice_result.scalar_one_or_none()

    return {
        "user_shop_id": user_shop.id,
        "last_invoice_id": last_invoice.id if last_invoice else None
    }


def create_access_token(
        user: User,
        user_shop_data: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT token with user data including shop and invoice information"""
    to_encode = {
        "user_id": user.id,
        "is_superuser": user.is_superuser,
        "sub": user.login
    }

    if user_shop_data:
        to_encode.update({
            "user_shop_id": user_shop_data.get("user_shop_id"),
            "last_invoice_id": user_shop_data.get("last_invoice_id")
        })

    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, str(settings.SECRET_KEY), algorithm=settings.ALGORITHM)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token with additional shop and invoice data"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, str(settings.SECRET_KEY), algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        user_shop_id: Optional[int] = payload.get("user_shop_id")
        last_invoice_id: Optional[int] = payload.get("last_invoice_id")
        is_superuser: bool = payload.get("is_superuser", False)

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=user_id,
            is_superuser=is_superuser
        )

        token_data.user_shop_id = user_shop_id
        token_data.last_invoice_id = last_invoice_id

    except JWTError:
        raise credentials_exception

    query = select(User).where(User.id == token_data.user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    user.current_shop_id = token_data.user_shop_id
    user.last_invoice_id = token_data.last_invoice_id

    return user
