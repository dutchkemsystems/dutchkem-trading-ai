"""Payment provider webhook and verification routes."""

import uuid
import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])


class WebhookResponse(BaseModel):
    message: str
    processed: bool


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    """Handle Paystack webhook callbacks."""
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(), body, hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    event_type = event.get("event", "")

    if event_type == "charge.success":
        data = event["data"]
        reference = data["reference"]
        amount_kobo = data["amount"]
        customer_email = data["customer"]["email"]

        return {"message": "Processed", "processed": True, "reference": reference}

    return {"message": "Event ignored", "processed": False}


@router.post("/flutterwave/webhook")
async def flutterwave_webhook(request: Request):
    """Handle Flutterwave webhook callbacks."""
    body = await request.body()
    signature = request.headers.get("verif-hash", "")

    if not hmac.compare_digest(
        hmac.new(settings.FLUTTERWAVE_SECRET_KEY.encode(), body, hashlib.sha512).hexdigest(),
        signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    event_type = event.get("event", "")

    if event_type == "charge.completed":
        data = event["data"]
        return {"message": "Processed", "processed": True, "transaction_id": data["id"]}

    return {"message": "Event ignored", "processed": False}


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook callbacks."""
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        from app.integrations.stripe_client import StripeClient
        stripe_client = StripeClient()
        event = stripe_client.verify_webhook(body, sig_header)
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        return {
            "message": "Processed",
            "processed": True,
            "session_id": session["id"],
            "payment_status": session["payment_status"],
        }

    return {"message": "Event ignored", "processed": False}


@router.get("/providers")
async def list_payment_providers():
    """List available payment providers."""
    return {
        "providers": [
            {
                "name": "Paystack",
                "id": "paystack",
                "currencies": ["NGN"],
                "type": "card",
                "region": "Nigeria",
            },
            {
                "name": "Flutterwave",
                "id": "flutterwave",
                "currencies": ["NGN", "GHS", "KES", "UGX", "TZS", "ZAR"],
                "type": "card",
                "region": "Africa-wide",
            },
            {
                "name": "Stripe",
                "id": "stripe",
                "currencies": ["USD", "EUR", "GBP"],
                "type": "card",
                "region": "International",
            },
        ]
    }
