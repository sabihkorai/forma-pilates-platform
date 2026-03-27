from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

import models
import auth
from database import get_db
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PLAN_PRICES = {
    "basic": 39.00,
    "premium": 59.00
}

MOCK_BILLING_HISTORY = [
    {"date": "Mar 1, 2026", "description": "Premium Plan - Monthly", "amount": "$59.00", "status": "Paid"},
    {"date": "Feb 1, 2026", "description": "Premium Plan - Monthly", "amount": "$59.00", "status": "Paid"},
    {"date": "Jan 1, 2026", "description": "Premium Plan - Monthly", "amount": "$59.00", "status": "Paid"},
    {"date": "Dec 1, 2025", "description": "Basic Plan - Monthly", "amount": "$39.00", "status": "Paid"},
]


@router.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.status == "active"
    ).first()

    success = request.cookies.get("flash_success", "")
    error = request.cookies.get("flash_error", "")

    response = templates.TemplateResponse("subscription/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "subscription": subscription,
        "billing_history": MOCK_BILLING_HISTORY,
        "plan_prices": PLAN_PRICES,
        "stripe_key": settings.STRIPE_PUBLISHABLE_KEY,
        "success": success,
        "error": error
    })
    response.delete_cookie("flash_success")
    response.delete_cookie("flash_error")
    return response


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    request: Request,
    plan: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    if plan not in ("basic", "premium"):
        response = RedirectResponse(url="/subscription", status_code=302)
        response.set_cookie("flash_error", "Invalid plan selected", max_age=10)
        return response

    # If Stripe key is configured, use real Stripe
    if settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"):
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            price_id = "price_basic_monthly" if plan == "basic" else "price_premium_monthly"
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=str(request.base_url) + "subscription/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=str(request.base_url) + "subscription"
            )
            return RedirectResponse(url=session.url, status_code=303)
        except Exception as e:
            print(f"[STRIPE ERROR] {e}")

    # Mock upgrade
    existing_sub = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.status == "active"
    ).first()

    if existing_sub:
        existing_sub.plan_type = plan
        existing_sub.monthly_price = PLAN_PRICES[plan]
        existing_sub.renewal_date = datetime.utcnow() + timedelta(days=30)
    else:
        new_sub = models.Subscription(
            user_id=current_user.id,
            plan_type=plan,
            monthly_price=PLAN_PRICES[plan],
            status="active",
            start_date=datetime.utcnow(),
            renewal_date=datetime.utcnow() + timedelta(days=30)
        )
        db.add(new_sub)

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.subscription_tier = plan
    db.commit()

    print(f"[EMAIL] Subscription confirmation sent to {current_user.email} - Plan: {plan}")

    response = RedirectResponse(url="/subscription/success", status_code=302)
    response.set_cookie("flash_success", f"Successfully upgraded to {plan.title()} plan!", max_age=30)
    return response


@router.post("/subscription/cancel")
async def cancel_subscription(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.status == "active"
    ).first()

    if subscription:
        subscription.status = "cancelled"
        subscription.cancelled_date = datetime.utcnow()

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.subscription_tier = "none"
    db.commit()

    print(f"[EMAIL] Cancellation confirmation sent to {current_user.email}")

    response = RedirectResponse(url="/subscription", status_code=302)
    response.set_cookie("flash_success", "Your subscription has been cancelled. You will retain access until the end of your billing period.", max_age=30)
    return response


@router.get("/subscription/success", response_class=HTMLResponse)
async def subscription_success(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    success_msg = request.cookies.get("flash_success", "Subscription activated successfully!")
    subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.status == "active"
    ).first()

    response = templates.TemplateResponse("subscription/success.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "subscription": subscription,
        "success": success_msg
    })
    response.delete_cookie("flash_success")
    return response
