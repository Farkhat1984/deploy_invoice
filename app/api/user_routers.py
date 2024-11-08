from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_db
from app.models.models import User
from app.crud.user_crud import get_user_shop_data, settings, create_access_token, verify_password, \
    get_current_user, get_password_hash
from app.schemas.schemas import UserResponse, UserCreate, Token
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_shop_data = await get_user_shop_data(session, user)

    access_token_expires = timedelta(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user=user,
        user_shop_data=user_shop_data,
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


async def authenticate_user(session: AsyncSession, login: str, password: str) -> Optional[User]:
    query = select(User).where(User.login == login)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def get_current_active_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user




@auth_router.post("/register", response_model=Token)
async def register_user(
        user_data: UserCreate,
        session: AsyncSession = Depends(get_db)
):
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        login=user_data.login,
        email=user_data.email,
        password=hashed_password,
        phone=user_data.phone
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    access_token_expires = timedelta(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user=new_user,
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/change-password")
async def change_password(
        old_password: str,
        new_password: str,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """Change user password"""
    if not verify_password(old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    current_user.password = get_password_hash(new_password)
    await session.commit()

    return {"message": "Password updated successfully"}


@auth_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
