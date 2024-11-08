from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


# Base Models with shared configurations
class BaseModelConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User Related Models
class UserBase(BaseModelConfig):
    login: str
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    shops_ids: List[int] = []


class UserResponse(UserBase):
    id: int
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime


class UserLogin(BaseModelConfig):
    login: str
    password: str


# Shop Related Models
class ShopBase(BaseModel):
    id: int
    name: str
    photo: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ShopCreate(ShopBase):
    pass


class ShopResponse(ShopBase):
    id: int
    created_at: datetime
    is_active: bool = True


# Authentication Related Models
class Token(BaseModelConfig):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModelConfig):
    user_id: int
    is_superuser: bool
    user_shop_id: Optional[int] = None
    last_invoice_id: Optional[int] = None

# Invoice Related Models
class InvoiceItemBase(BaseModel):
    name: str
    quantity: float
    price: float
    total: float

    model_config = ConfigDict(from_attributes=True)


class InvoiceItemCreate(BaseModel):
    name: str
    quantity: float
    price: float
    total: float

    model_config = ConfigDict(from_attributes=True)


class InvoiceItemResponse(InvoiceItemBase):
    id: int


class InvoiceBase(BaseModelConfig):
    contact_info: Optional[str] = None
    additional_info: Optional[str] = None


class InvoiceCreate(BaseModel):
    shop_id: int
    contact_info: Optional[str] = None
    additional_info: Optional[str] = None
    total_amount: float
    is_paid: bool = False
    items: List[InvoiceItemCreate] = []  # Добавляем поле для items

    model_config = ConfigDict(from_attributes=True)


class InvoiceFilter(BaseModelConfig):
    shop_id: Optional[int] = None
    is_paid: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None


class InvoiceResponse(BaseModel):
    id: int
    created_at: datetime
    contact_info: Optional[str] = None
    additional_info: Optional[str] = None
    total_amount: float
    is_paid: bool
    shop_id: int
    user_id: int
    shop: ShopBase
    items: List[InvoiceItemBase] = []

    model_config = ConfigDict(from_attributes=True)


class InvoiceItemUpdate(BaseModel):
    name: str
    quantity: float
    price: float

    model_config = ConfigDict(from_attributes=True)


class InvoiceUpdate(BaseModel):
    contact_info: Optional[str] = None
    additional_info: Optional[str] = None
    is_paid: Optional[bool] = None
    items: Optional[List[InvoiceItemUpdate]] = None

    model_config = ConfigDict(from_attributes=True)
