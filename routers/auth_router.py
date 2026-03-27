from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import re

import models
import auth
from database import get_db
from config import settings

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


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = auth.get_current_user_optional(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    error = request.cookies.get("flash_error", "")
    response = templates.TemplateResponse("auth/login.html", {
        "request": request,
        "current_user": None,
        "error": error
    })
    response.delete_cookie("flash_error")
    return response


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not auth.verify_password(password, user.password_hash):
        response = RedirectResponse(url="/login", status_code=302)
        response.set_cookie("flash_error", "Invalid email or password", max_age=5)
        return response

    access_token = auth.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    response.set_cookie("flash_success", f"Welcome back, {user.full_name.split()[0]}!", max_age=5)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = auth.get_current_user_optional(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    error = request.cookies.get("flash_error", "")
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "current_user": None,
        "error": error
    })


@router.post("/register")
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    plan: str = Form(default="none"),
    newsletter: str = Form(default="off"),
    card_number: str = Form(default=""),
    card_expiry: str = Form(default=""),
    card_cvv: str = Form(default=""),
    db: Session = Depends(get_db)
):
    if not phone or not phone.strip():
        response = RedirectResponse(url="/register", status_code=302)
        response.set_cookie("flash_error", "Phone number is required", max_age=5)
        return response

    if password != confirm_password:
        response = RedirectResponse(url="/register", status_code=302)
        response.set_cookie("flash_error", "Passwords do not match", max_age=5)
        return response

    pwd_error = validate_password(password)
    if pwd_error:
        response = RedirectResponse(url="/register", status_code=302)
        response.set_cookie("flash_error", pwd_error, max_age=5)
        return response

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        response = RedirectResponse(url="/register", status_code=302)
        response.set_cookie("flash_error", "Email already registered", max_age=5)
        return response

    hashed = auth.hash_password(password)
    user = models.User(
        full_name=full_name,
        email=email,
        phone=phone.strip(),
        password_hash=hashed,
        subscription_tier=plan if plan in ("basic", "premium") else "none",
        avatar_url=f"https://ui-avatars.com/api/?name={full_name.replace(' ', '+')}&background=1A1A1A&color=fff&size=128",
        trial_end_date=datetime.utcnow() + timedelta(days=15),
        trial_used=True,
        payment_method_token=f"mock_pm_{email}",
        newsletter_opt_in=(newsletter == "on")
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"[EMAIL] Welcome email sent to {email} - Welcome to Forma Pilates, {full_name}!")

    access_token = auth.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    response.set_cookie("flash_success", f"Welcome to Forma, {full_name.split()[0]}!", max_age=5)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    response.set_cookie("flash_success", "You have been logged out", max_age=5)
    return response
