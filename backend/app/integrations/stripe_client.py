"""Stripe integration for international USD payments."""

import stripe
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class StripeClient:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    def create_checkout_session(
        self,
        amount_cents: int,
        currency: str = "usd",
        customer_email: str | None = None,
        success_url: str = "",
        cancel_url: str = "",
        metadata: dict | None = None,
    ) -> stripe.checkout.Session:
        params: dict = {
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": "Dutchkem Fortress - Agentic Fuel Credits",
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata or {},
        }
        if customer_email:
            params["customer_email"] = customer_email
        return stripe.checkout.Session.create(**params)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    def create_customer(self, email: str, name: str | None = None) -> stripe.Customer:
        params: dict = {"email": email}
        if name:
            params["name"] = name
        return stripe.Customer.create(**params)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    def create_subscription(
        self, customer_id: str, price_id: str, trial_days: int | None = None
    ) -> stripe.Subscription:
        params: dict = {
            "customer": customer_id,
            "items": [{"price": price_id}],
        }
        if trial_days:
            params["trial_period_days"] = trial_days
        return stripe.Subscription.create(**params)

    def verify_webhook(self, payload: bytes, sig_header: str) -> stripe.Event:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
