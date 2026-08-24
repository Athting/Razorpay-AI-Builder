"""
Stopping Rules router — CRUD for compliance-enforcement rules.
"""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid as uuid_lib
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.models.stopping_rule import StoppingRule, RuleAppliesTo
from app.schemas import StoppingRuleCreate, StoppingRuleUpdate, StoppingRuleResponse

router = APIRouter(prefix="/stopping-rules", tags=["stopping-rules"])


@router.get("", response_model=List[StoppingRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    result = await db.execute(select(StoppingRule).where(StoppingRule.organization_id == organization.id).order_by(StoppingRule.created_at))
    return [StoppingRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=StoppingRuleResponse, status_code=201)
async def create_rule(
    body: StoppingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    rule = StoppingRule(
        id=uuid_lib.uuid4(),
        organization_id=organization.id,
        name=body.name,
        max_attempts=body.max_attempts,
        cooldown_hours=body.cooldown_hours,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
        applies_to=RuleAppliesTo(body.applies_to),
        active=body.active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return StoppingRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=StoppingRuleResponse)
async def update_rule(
    rule_id: UUID,
    body: StoppingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    result = await db.execute(select(StoppingRule).where(StoppingRule.id == rule_id, StoppingRule.organization_id == organization.id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.name = body.name
    rule.max_attempts = body.max_attempts
    rule.cooldown_hours = body.cooldown_hours
    rule.quiet_hours_start = body.quiet_hours_start
    rule.quiet_hours_end = body.quiet_hours_end
    rule.applies_to = RuleAppliesTo(body.applies_to)
    rule.active = body.active
    rule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(rule)
    return StoppingRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    result = await db.execute(select(StoppingRule).where(StoppingRule.id == rule_id, StoppingRule.organization_id == organization.id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.active = False  # soft delete
    await db.commit()
