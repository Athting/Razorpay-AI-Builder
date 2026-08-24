"""
Customers router — Customer list and DND management.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.models import Customer
from app.schemas import CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    search: Optional[str] = Query(None),
    dnd_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    stmt = select(Customer).where(Customer.organization_id == organization.id).order_by(Customer.name)
    if dnd_only:
        stmt = stmt.where(Customer.dnd_opt_out == True)
    if search:
        from sqlalchemy import or_
        stmt = stmt.where(or_(
            Customer.name.ilike(f"%{search}%"),
            Customer.email.ilike(f"%{search}%"),
            Customer.phone.ilike(f"%{search}%"),
        ))
    result = await db.execute(stmt.limit(100))
    customers = result.scalars().all()
    return [
        CustomerResponse(
            id=c.id, name=c.name, email=c.email, phone=c.phone,
            segment=c.segment, risk_score=c.risk_score, dnd_opt_out=c.dnd_opt_out,
            channel_opts=c.channel_opts, city=c.city, created_at=c.created_at,
            tenure_days=c.tenure_days,
        )
        for c in customers
    ]


@router.post("/{customer_id}/opt-out")
async def opt_out(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.organization_id == organization.id))
    customer = result.scalar_one_or_none()
    if not customer:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.dnd_opt_out = True
    await db.commit()
    return {"status": "opted_out"}


@router.post("/{customer_id}/opt-in")
async def opt_in(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.organization_id == organization.id))
    customer = result.scalar_one_or_none()
    if not customer:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.dnd_opt_out = False
    await db.commit()
    return {"status": "opted_in"}
