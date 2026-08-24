"""Merchant payment-link creation via the workspace's own Razorpay account."""
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import get_db
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.core.secrets import unseal

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentLinkRequest(BaseModel):
    amount_paise: int = Field(gt=99)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, max_length=20)
    description: str = Field(default="Payment request", max_length=255)
    reference_id: str | None = Field(default=None, max_length=40)


@router.post("/payment-links")
async def create_payment_link(
    payload: PaymentLinkRequest,
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    credentials = unseal(organization.razorpay_oauth_config)
    auth_type = credentials.get("auth_type", "key_secret")
    if auth_type == "oauth" and credentials.get("access_token"):
        auth_headers = {"Authorization": f"Bearer {credentials['access_token']}"}
        auth = None
    elif organization.razorpay_key_id and credentials.get("key_secret"):
        auth_headers = None
        auth = (organization.razorpay_key_id, credentials["key_secret"])
    else:
        raise HTTPException(status_code=409, detail="Connect Razorpay in workspace settings before creating payment links")

    body = {
        "amount": payload.amount_paise,
        "currency": "INR",
        "description": payload.description,
        "customer": {"name": payload.customer_name},
        "notify": {"sms": bool(payload.customer_phone), "email": bool(payload.customer_email)},
    }
    if payload.customer_email:
        body["customer"]["email"] = str(payload.customer_email)
    if payload.customer_phone:
        body["customer"]["contact"] = payload.customer_phone
    if payload.reference_id:
        body["reference_id"] = payload.reference_id

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/payment_links",
                auth=auth,
                headers=auth_headers,
                json=body,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Razorpay could not be reached") from exc
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail="Razorpay rejected the payment-link request")

    result = response.json()
    return {"id": result.get("id"), "short_url": result.get("short_url"), "status": result.get("status")}
