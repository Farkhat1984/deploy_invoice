from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Table, Numeric, MetaData
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    metadata = MetaData()


# Association table for users and shops many-to-many relationship
users_shops = Table(
    'users_shops',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('shop_id', Integer, ForeignKey('shops.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """User model representing system users"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    shops: Mapped[List["Shop"]] = relationship(
        "Shop",
        secondary=users_shops,
        back_populates="users",
        cascade="all, delete"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Shop(Base):
    """Shop model representing business entities"""
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    photo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    additional_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=users_shops,
        back_populates="shops",
        cascade="all, delete"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="shop",
        cascade="all, delete-orphan"
    )


class Invoice(Base):
    """Invoice model representing sales documents"""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    contact_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0
    )
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign Keys
    shop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="invoices")
    user: Mapped["User"] = relationship("User", back_populates="invoices")
    items: Mapped[List["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )


class InvoiceItem(Base):
    """Model representing individual items within an invoice"""
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        default=1
    )
    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0
    )
    total: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0
    )

    # Foreign Key
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationship
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")