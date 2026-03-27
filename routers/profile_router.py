from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import re

import models
import auth
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def validate_password(password: str):
    """Returns error message or None if valid."""
    if len(password) < 6:
        return "Password must be at least 6 characters"
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least 1 uppercase letter"
    if not re.search(r'[0-9]', password):
        return "Password must contain at least 1 number"
    special_chars = r'[=+\-_)(/*&^%$#@!~`|}\]{\'\";:/?.,><\\]'
    if not re.search(special_chars, password):
        return "Password must contain at least 1 special character"
    return None


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    success = request.cookies.get("flash_success", "")
    error = request.cookies.get("flash_error", "")
    delete_error = request.cookies.get("delete_error", "")
    response = templates.TemplateResponse("profile/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "success": success,
        "error": error,
        "delete_error": delete_error
    })
    response.delete_cookie("flash_success")
    response.delete_cookie("flash_error")
    response.delete_cookie("delete_error")
    return response


@router.post("/profile/update", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    bio: Optional[str] = Form(default=None),
    health_notes: Optional[str] = Form(default=None),
    height_cm: Optional[float] = Form(default=None),
    weight_lbs: Optional[float] = Form(default=None),
    target_weight_lbs: Optional[float] = Form(default=None),
    age: Optional[int] = Form(default=None),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<div class="text-red-500 p-3 bg-red-50 rounded-xl">Not authenticated</div>')

    if not phone or not phone.strip():
        return HTMLResponse('<div class="text-red-500 p-3 bg-red-50 rounded-xl border border-red-200">Phone number is required</div>')

    # Check email uniqueness
    if email != current_user.email:
        existing = db.query(models.User).filter(
            models.User.email == email,
            models.User.id != current_user.id
        ).first()
        if existing:
            return HTMLResponse('<div class="text-red-500 p-3 bg-red-50 rounded-xl border border-red-200">Email already in use by another account</div>')

    # Convert lbs to kg
    weight_kg = weight_lbs / 2.205 if weight_lbs else None
    target_weight_kg = target_weight_lbs / 2.205 if target_weight_lbs else None

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.full_name = full_name
    db_user.email = email
    db_user.phone = phone.strip()
    db_user.bio = bio
    db_user.health_notes = health_notes
    db_user.height_cm = height_cm
    db_user.weight_kg = weight_kg
    db_user.target_weight_kg = target_weight_kg
    db_user.age = age
    db_user.avatar_url = f"https://ui-avatars.com/api/?name={full_name.replace(' ', '+')}&background=1A1A1A&color=fff&size=128"

    db.commit()

    print(f"[EMAIL] Profile update confirmation sent to {email}")

    return HTMLResponse('''
        <div class="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
            <div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
            </div>
            <div>
                <p class="font-semibold text-green-800">Profile updated successfully!</p>
                <p class="text-sm text-green-600">Your changes have been saved.</p>
            </div>
        </div>
    ''')


@router.post("/profile/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<div class="text-red-500 p-3 bg-red-50 rounded-xl">Not authenticated</div>')

    if not auth.verify_password(current_password, current_user.password_hash):
        return HTMLResponse('<div class="text-red-500 p-3 bg-red-50 rounded-xl border border-red-200">Current password is incorrect</div>')

    if new_password != confirm_password:
        return HTMLResponse('<div class="text-red-500 p-3 bg-red-50 rounded-xl border border-red-200">New passwords do not match</div>')

    pwd_error = validate_password(new_password)
    if pwd_error:
        return HTMLResponse(f'<div class="text-red-500 p-3 bg-red-50 rounded-xl border border-red-200">{pwd_error}</div>')

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.password_hash = auth.hash_password(new_password)
    db.commit()

    return HTMLResponse('''
        <div class="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
            <div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
            </div>
            <div>
                <p class="font-semibold text-green-800">Password changed successfully!</p>
                <p class="text-sm text-green-600">Please use your new password next time you log in.</p>
            </div>
        </div>
    ''')


@router.post("/profile/delete")
async def delete_account(
    request: Request,
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    if not auth.verify_password(confirm_password, current_user.password_hash):
        response = RedirectResponse(url="/profile", status_code=302)
        response.set_cookie("delete_error", "Incorrect password. Account not deleted.", max_age=10)
        return response

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if db_user:
        db_user.is_active = False
        db.commit()

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.post("/profile/newsletter-toggle")
async def newsletter_toggle(
    request: Request,
    opt_in: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.newsletter_opt_in = (opt_in == "true")
    db.commit()
    response = RedirectResponse(url="/profile", status_code=302)
    response.set_cookie("flash_success", "Email preferences updated.", max_age=10)
    return response
