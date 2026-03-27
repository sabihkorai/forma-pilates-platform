from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import random
import string

import models
import auth
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def generate_gift_code():
    """Generate a unique 12-character gift code."""
    chars = string.ascii_uppercase + string.digits
    return "FORMA-" + "".join(random.choices(chars, k=6))


@router.get("/gift", response_class=HTMLResponse)
async def gift_page(request: Request):
    current_user = auth.get_current_user_optional(request)
    error = request.cookies.get("flash_error", "")
    response = templates.TemplateResponse("gift/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium" if current_user else False,
        "error": error
    })
    response.delete_cookie("flash_error")
    return response


@router.post("/gift/purchase")
async def purchase_gift(
    request: Request,
    purchaser_name: str = Form(...),
    purchaser_email: str = Form(...),
    recipient_name: str = Form(...),
    recipient_email: str = Form(...),
    plan_type: str = Form(...),
    personal_message: Optional[str] = Form(default=None),
    delivery_date: Optional[str] = Form(default=None),
    card_number: str = Form(default=""),
    card_expiry: str = Form(default=""),
    card_cvv: str = Form(default=""),
    db: Session = Depends(get_db)
):
    current_user = auth.get_current_user_optional(request)

    amount = 59.0 if plan_type == "premium" else 39.0

    # Generate unique code
    gift_code = generate_gift_code()
    while db.query(models.GiftCertificate).filter(models.GiftCertificate.gift_code == gift_code).first():
        gift_code = generate_gift_code()

    delivery_dt = None
    if delivery_date:
        try:
            delivery_dt = datetime.strptime(delivery_date, "%Y-%m-%d")
        except Exception:
            delivery_dt = datetime.utcnow()

    cert = models.GiftCertificate(
        purchaser_user_id=current_user.id if current_user else None,
        purchaser_name=purchaser_name,
        purchaser_email=purchaser_email,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        plan_type=plan_type,
        amount=amount,
        gift_code=gift_code,
        personal_message=personal_message,
        delivery_date=delivery_dt or datetime.utcnow()
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    print(f"[EMAIL] Gift certificate {gift_code} sent to {recipient_email} from {purchaser_name}")

    return templates.TemplateResponse("gift/success.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium" if current_user else False,
        "cert": cert
    })


@router.get("/gift/redeem", response_class=HTMLResponse)
async def redeem_page(request: Request):
    current_user = auth.get_current_user_optional(request)
    error = request.cookies.get("flash_error", "")
    success = request.cookies.get("flash_success", "")
    response = templates.TemplateResponse("gift/redeem.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium" if current_user else False,
        "error": error,
        "success": success
    })
    response.delete_cookie("flash_error")
    response.delete_cookie("flash_success")
    return response


@router.post("/gift/redeem")
async def redeem_gift(
    request: Request,
    gift_code: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        response = RedirectResponse(url="/login", status_code=302)
        response.set_cookie("flash_error", "Please log in to redeem a gift certificate.", max_age=5)
        return response

    cert = db.query(models.GiftCertificate).filter(
        models.GiftCertificate.gift_code == gift_code.strip().upper()
    ).first()

    if not cert:
        response = RedirectResponse(url="/gift/redeem", status_code=302)
        response.set_cookie("flash_error", "Invalid gift code. Please check and try again.", max_age=5)
        return response

    if cert.is_redeemed:
        response = RedirectResponse(url="/gift/redeem", status_code=302)
        response.set_cookie("flash_error", "This gift certificate has already been redeemed.", max_age=5)
        return response

    # Apply to user account
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.subscription_tier = cert.plan_type
    cert.is_redeemed = True
    cert.redeemed_by_user_id = current_user.id
    cert.redeemed_at = datetime.utcnow()
    db.commit()

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("flash_success", f"Gift certificate redeemed! You now have {cert.plan_type.title()} access.", max_age=5)
    return response
