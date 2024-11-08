from typing import List
from fastapi import HTTPException
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.models import users_shops, User, Invoice, InvoiceItem, Shop
from app.schemas.schemas import InvoiceCreate, InvoiceUpdate, InvoiceFilter


async def insert_invoice(
        session: AsyncSession,
        invoice_data: InvoiceCreate,
        current_user: User
) -> Invoice:
    async with session.begin_nested():

        has_access = await check_user_shop_access(
            session,
            current_user.id,
            invoice_data.shop_id
        )
        if not has_access:
            raise HTTPException(status_code=403, detail="No access to this shop")

        shop_query = select(Shop).where(Shop.id == invoice_data.shop_id)
        shop_result = await session.execute(shop_query)
        shop = shop_result.scalar_one_or_none()

        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")

        new_invoice = Invoice(
            shop_id=invoice_data.shop_id,
            user_id=current_user.id,
            contact_info=invoice_data.contact_info,
            additional_info=invoice_data.additional_info,
            total_amount=invoice_data.total_amount,
            is_paid=invoice_data.is_paid
        )

        session.add(new_invoice)
        await session.flush()

        if hasattr(invoice_data, 'items'):
            for item_data in invoice_data.items:
                item = InvoiceItem(
                    invoice_id=new_invoice.id,
                    name=item_data.name,
                    quantity=item_data.quantity,
                    price=item_data.price,
                    total=item_data.total
                )
                session.add(item)

    await session.commit()

    query = select(Invoice).options(
        selectinload(Invoice.shop),
        selectinload(Invoice.items)
    ).where(
        Invoice.id == new_invoice.id
    )

    result = await session.execute(query)
    invoice = result.unique().scalar_one()

    return invoice


async def check_user_shop_access(
        session: AsyncSession,
        user_id: int,
        shop_id: int
) -> bool:
    query = select(users_shops).where(
        and_(
            users_shops.c.user_id == user_id,
            users_shops.c.shop_id == shop_id
        )
    )
    result = await session.execute(query)
    return result.first() is not None


async def update_invoice_db(
        session: AsyncSession,
        invoice_id: int,
        invoice_data: InvoiceUpdate,
        current_user: User
) -> Invoice:
    async with session.begin_nested():
        query = select(Invoice).options(
            selectinload(Invoice.items),
            selectinload(Invoice.shop)
        ).where(Invoice.id == invoice_id)

        result = await session.execute(query)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can update invoices")
        if invoice_data.contact_info is not None:
            invoice.contact_info = invoice_data.contact_info
        if invoice_data.additional_info is not None:
            invoice.additional_info = invoice_data.additional_info
        if invoice_data.is_paid is not None:
            invoice.is_paid = invoice_data.is_paid

        if invoice_data.items:
            delete_stmt = delete(InvoiceItem).where(
                InvoiceItem.invoice_id == invoice_id
            )
            await session.execute(delete_stmt)

            total_amount = 0
            for item_data in invoice_data.items:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    name=item_data.name,
                    quantity=item_data.quantity,
                    price=item_data.price,
                    total=item_data.quantity * item_data.price
                )
                total_amount += item.total
                session.add(item)

            invoice.total_amount = total_amount

    await session.commit()

    refresh_query = select(Invoice).options(
        selectinload(Invoice.items),
        selectinload(Invoice.shop)
    ).where(Invoice.id == invoice_id)

    result = await session.execute(refresh_query)
    updated_invoice = result.unique().scalar_one()

    return updated_invoice


async def delete_invoice_db(
        session: AsyncSession,
        invoice_id: int,
        current_user: User
) -> bool:
    query = select(Invoice).where(Invoice.id == invoice_id)
    result = await session.execute(query)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Check permissions
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only admins can delete invoices")

    await session.delete(invoice)
    await session.commit()
    return True


async def fetch_invoice(
        session: AsyncSession,
        invoice_id: int,
        current_user: User
) -> Invoice:
    query = select(Invoice).options(
        joinedload(Invoice.items),
        joinedload(Invoice.shop),
        joinedload(Invoice.user)
    ).where(Invoice.id == invoice_id)

    result = await session.execute(query)
    invoice = result.unique().scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    has_access = await check_user_shop_access(session, current_user.id, invoice.shop_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this invoice")

    return invoice


async def fetch_invoices_with_filters(
        session: AsyncSession,
        current_user: User,
        filters: InvoiceFilter,
        skip: int = 0,
        limit: int = 100
) -> List[Invoice]:
    query = select(Invoice).options(
        joinedload(Invoice.items),
        joinedload(Invoice.shop),
        joinedload(Invoice.user)
    )

    shops_query = select(users_shops.c.shop_id).where(
        users_shops.c.user_id == current_user.id
    )
    result = await session.execute(shops_query)
    accessible_shops = [row[0] for row in result.fetchall()]

    query = query.where(Invoice.shop_id.in_(accessible_shops))

    if filters.shop_id:
        if filters.shop_id not in accessible_shops:
            raise HTTPException(status_code=403, detail="No access to this shop")
        query = query.where(Invoice.shop_id == filters.shop_id)

    if filters.is_paid is not None:
        query = query.where(Invoice.is_paid == filters.is_paid)

    if filters.created_after:
        query = query.where(Invoice.created_at >= filters.created_after)

    if filters.created_before:
        query = query.where(Invoice.created_at <= filters.created_before)

    if filters.min_amount is not None:
        query = query.where(Invoice.total_amount >= filters.min_amount)

    if filters.max_amount is not None:
        query = query.where(Invoice.total_amount <= filters.max_amount)

    query = query.order_by(Invoice.created_at.desc())

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    invoices = result.unique().scalars().all()

    for invoice in invoices:
        if hasattr(invoice, 'created_at') and invoice.created_at:
            invoice.formatted_date = invoice.created_at.strftime("%d-%m-%y %H:%M")

    return invoices
