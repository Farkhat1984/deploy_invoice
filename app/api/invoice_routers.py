from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.core.config import get_db
from app.api.user_routers import get_current_user, create_access_token
from app.crud.invoice_crud import fetch_invoice, fetch_invoices_with_filters, insert_invoice, check_user_shop_access, \
    update_invoice_db, delete_invoice_db
from app.models.models import User, Invoice
from app.schemas.schemas import InvoiceCreate, InvoiceResponse, InvoiceFilter, InvoiceUpdate

router = APIRouter(prefix="/api/v1")


@router.get("/invoices/last", response_model=InvoiceResponse)
async def get_last_invoice(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        if current_user.last_invoice_id:
            invoice = await fetch_invoice(session, current_user.last_invoice_id, current_user)
            return invoice
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No last invoice found"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/stats/summary")
async def get_invoice_stats(
        shop_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        if not shop_id and current_user.current_shop_id:
            shop_id = current_user.current_shop_id

        query = select(
            func.count(Invoice.id).label('total_invoices'),
            func.sum(Invoice.total_amount).label('total_amount'),
            func.avg(Invoice.total_amount).label('average_amount'),
            func.sum(case((Invoice.is_paid, 1), else_=0)).label('paid_invoices'),
        )

        if shop_id:
            has_access = await check_user_shop_access(session, current_user.id, shop_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="No access to this shop")
            query = query.where(Invoice.shop_id == shop_id)

        if start_date:
            query = query.where(Invoice.created_at >= start_date)
        if end_date:
            query = query.where(Invoice.created_at <= end_date)

        result = await session.execute(query)
        stats = result.first()

        total_invoices = stats.total_invoices or 0
        total_amount = float(stats.total_amount or 0)
        average_amount = float(stats.average_amount or 0)
        paid_invoices = stats.paid_invoices or 0

        return {
            "total_invoices": total_invoices,
            "total_amount": total_amount,
            "average_amount": average_amount,
            "paid_invoices": paid_invoices,
            "unpaid_invoices": total_invoices - paid_invoices,
            "shop_id": shop_id
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/invoices/', response_model=InvoiceResponse, status_code=201)
async def create_invoice(
        invoice_data: InvoiceCreate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        if not invoice_data.shop_id and current_user.current_shop_id:
            invoice_data.shop_id = current_user.current_shop_id

        invoice = await insert_invoice(
            session=session,
            invoice_data=invoice_data,
            current_user=current_user
        )

        if invoice.shop_id == current_user.current_shop_id:
            current_user.last_invoice_id = invoice.id
            user_shop_data = {
                "user_shop_id": current_user.current_shop_id,
                "last_invoice_id": invoice.id
            }
            new_token = create_access_token(current_user, user_shop_data)
            invoice.new_token = new_token

        return invoice

    except HTTPException as e:
        await session.rollback()
        raise e
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/invoices/", response_model=List[InvoiceResponse])
async def list_invoices(
        shop_id: Optional[int] = None,
        is_paid: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=100, le=100),
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    if not shop_id and current_user.current_shop_id:
        shop_id = current_user.current_shop_id

    filters = InvoiceFilter(
        shop_id=shop_id,
        is_paid=is_paid,
        created_after=created_after,
        created_before=created_before,
        min_amount=min_amount,
        max_amount=max_amount
    )
    try:
        invoices = await fetch_invoices_with_filters(
            session,
            current_user,
            filters,
            skip,
            limit
        )
        return invoices
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
        invoice_id: int,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        invoice = await fetch_invoice(session, invoice_id, current_user)
        return invoice
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
        invoice_id: int,
        invoice_data: InvoiceUpdate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        invoice = await update_invoice_db(
            session,
            invoice_id,
            invoice_data,
            current_user
        )
        return invoice
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
        invoice_id: int,
        is_paid: bool,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    update_data = InvoiceUpdate(is_paid=is_paid)
    try:
        invoice = await update_invoice_db(
            session,
            invoice_id,
            update_data,
            current_user
        )
        return invoice
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invoices/{invoice_id}", status_code=204)
async def delete_invoice(
        invoice_id: int,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        await delete_invoice_db(session, invoice_id, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
