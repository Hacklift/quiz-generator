from datetime import datetime, timezone
from typing import Literal

import stripe
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel

from server.app.db.core.config import settings
from server.app.db.core.connection import get_users_collection
from server.app.db.core.rate_limiter import RateLimits, limiter
from server.app.db.models.user_models import UserOut
from server.app.dependancies import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CreateCheckoutSessionRequest(BaseModel):
    plan: Literal["monthly", "yearly"]


class CreateCheckoutSessionResponse(BaseModel):
    checkout_url: str


class CreatePortalSessionResponse(BaseModel):
    portal_url: str


class SubscriptionResponse(BaseModel):
    subscription_plan: str = "free"
    subscription_status: str = "inactive"
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: str | None = None


def _get_price_id(plan: str) -> str:
    price_id_map = {
        "monthly": settings.STRIPE_PRICE_ID_MONTHLY,
        "yearly": settings.STRIPE_PRICE_ID_YEARLY,
    }
    price_id = price_id_map.get(plan)
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe price ID for the {plan} plan is not configured",
        )
    return price_id


def _get_stripe_client() -> stripe:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _normalize_timestamp(value: int | None) -> str | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _infer_plan_from_subscription(subscription: stripe.Subscription | None) -> str | None:
    if subscription is None:
        return None

    price_id = (
        subscription.get("items", {})
        .get("data", [{}])[0]
        .get("price", {})
        .get("id")
    )

    if price_id == settings.STRIPE_PRICE_ID_MONTHLY:
        return "monthly"
    if price_id == settings.STRIPE_PRICE_ID_YEARLY:
        return "yearly"
    return None


async def _find_user_by_customer_id(
    users_collection: AsyncIOMotorCollection,
    customer_id: str | None,
):
    if not customer_id:
        return None
    return await users_collection.find_one({"stripe_customer_id": customer_id})


async def _persist_subscription_state(
    users_collection: AsyncIOMotorCollection,
    user_filter: dict,
    subscription: stripe.Subscription | None,
    fallback_plan: str | None = None,
):
    update_data = {
        "updated_at": datetime.now(timezone.utc),
    }

    if subscription is None:
        update_data.update(
            {
                "subscription_plan": "free",
                "subscription_status": "inactive",
                "stripe_subscription_id": None,
                "current_period_end": None,
            }
        )
    else:
        plan = (
            fallback_plan
            or subscription.get("metadata", {}).get("plan")
            or _infer_plan_from_subscription(subscription)
            or "monthly"
        )
        update_data.update(
            {
                "subscription_plan": plan,
                "subscription_status": subscription.get("status", "inactive"),
                "stripe_subscription_id": subscription.get("id"),
                "current_period_end": _normalize_timestamp(
                    subscription.get("current_period_end")
                ),
            }
        )

    await users_collection.update_one(user_filter, {"$set": update_data})


@router.post(
    "/create-checkout-session",
    response_model=CreateCheckoutSessionResponse,
)
@limiter.limit(RateLimits.API_WRITE)
async def create_checkout_session(
    request: Request,
    payload: CreateCheckoutSessionRequest,
    current_user: UserOut = Depends(get_current_user),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
):
    stripe_client = _get_stripe_client()
    price_id = _get_price_id(payload.plan)

    user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe_client.Customer.create(
            email=current_user.email,
            name=current_user.full_name or current_user.username,
            metadata={"user_id": current_user.id},
        )
        customer_id = customer["id"]
        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "stripe_customer_id": customer_id,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    session = stripe_client.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_BASE_URL}/profile?payment=success",
        cancel_url=f"{settings.FRONTEND_BASE_URL}/?payment=cancelled#pricing",
        client_reference_id=current_user.id,
        metadata={"user_id": current_user.id, "plan": payload.plan},
        allow_promotion_codes=True,
    )

    return CreateCheckoutSessionResponse(checkout_url=session.url)


@router.post("/create-portal-session", response_model=CreatePortalSessionResponse)
@limiter.limit(RateLimits.API_WRITE)
async def create_portal_session(
    request: Request,
    current_user: UserOut = Depends(get_current_user),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
):
    stripe_client = _get_stripe_client()

    user = await users_collection.find_one({"_id": ObjectId(current_user.id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe customer is associated with this account yet",
        )

    session = stripe_client.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.FRONTEND_BASE_URL}/profile",
    )
    return CreatePortalSessionResponse(portal_url=session.url)


@router.get("/subscription", response_model=SubscriptionResponse)
@limiter.limit(RateLimits.API_READ)
async def get_subscription(
    request: Request,
    current_user: UserOut = Depends(get_current_user),
):
    return SubscriptionResponse(
        subscription_plan=current_user.subscription_plan or "free",
        subscription_status=current_user.subscription_status or "inactive",
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        current_period_end=current_user.current_period_end,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
):
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id") or data.get("client_reference_id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id:
            subscription = None
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
            await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "stripe_customer_id": customer_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            await _persist_subscription_state(
                users_collection,
                {"_id": ObjectId(user_id)},
                subscription,
                fallback_plan=data.get("metadata", {}).get("plan"),
            )

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        user = await _find_user_by_customer_id(users_collection, customer_id)
        if user:
            await _persist_subscription_state(
                users_collection,
                {"_id": user["_id"]},
                data,
            )

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        user = await _find_user_by_customer_id(users_collection, customer_id)
        if user:
            await _persist_subscription_state(
                users_collection,
                {"_id": user["_id"]},
                None,
            )

    elif event_type == "invoice.paid":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        user = await _find_user_by_customer_id(users_collection, customer_id)
        if user and subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            await _persist_subscription_state(
                users_collection,
                {"_id": user["_id"]},
                subscription,
            )

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        user = await _find_user_by_customer_id(users_collection, customer_id)
        if user:
            await users_collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "subscription_status": "past_due",
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

    return {"received": True}
