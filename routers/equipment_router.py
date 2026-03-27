from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

import models
import auth
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

EQUIPMENT_LIST = [
    "Premium Pilates Mat (6mm, non-slip)",
    "Resistance Bands Set (3 strengths)",
    "Pilates Ring / Magic Circle",
    "Pilates Grip Socks (2 pairs)",
    "Foam Roller (Full size)"
]


@router.get("/equipment", response_class=HTMLResponse)
async def equipment_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    equipment_loan = db.query(models.EquipmentLoan).filter(
        models.EquipmentLoan.user_id == current_user.id
    ).first()

    ownership_date = None
    days_until_ownership = None
    if equipment_loan and equipment_loan.delivered_date:
        ownership_date = equipment_loan.delivered_date + timedelta(days=180)
        delta = ownership_date - datetime.utcnow()
        days_until_ownership = max(0, delta.days)

    success = request.cookies.get("flash_success", "")
    response = templates.TemplateResponse("equipment/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "equipment_loan": equipment_loan,
        "equipment_list": EQUIPMENT_LIST,
        "ownership_date": ownership_date,
        "days_until_ownership": days_until_ownership,
        "success": success
    })
    response.delete_cookie("flash_success")
    return response


@router.post("/equipment/request")
async def request_equipment(
    request: Request,
    shipping_address: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    if current_user.subscription_tier != "premium":
        return RedirectResponse(url="/subscription", status_code=302)

    existing = db.query(models.EquipmentLoan).filter(
        models.EquipmentLoan.user_id == current_user.id
    ).first()

    if not existing:
        subscription = db.query(models.Subscription).filter(
            models.Subscription.user_id == current_user.id,
            models.Subscription.status == "active"
        ).first()

        loan = models.EquipmentLoan(
            user_id=current_user.id,
            subscription_id=subscription.id if subscription else None,
            equipment_list=json.dumps(EQUIPMENT_LIST),
            loan_value=200.0,
            status="pending",
            shipping_address=shipping_address,
            shipped_date=datetime.utcnow() + timedelta(days=2),
            delivered_date=datetime.utcnow() + timedelta(days=7)
        )
        db.add(loan)
        db.commit()

        print(f"[EMAIL] Equipment request confirmation sent to {current_user.email}")

    response = RedirectResponse(url="/equipment", status_code=302)
    response.set_cookie("flash_success", "Your equipment kit has been requested! Expected delivery in 5-7 business days.", max_age=30)
    return response
