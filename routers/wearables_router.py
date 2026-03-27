from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

import models
import auth
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DEVICE_DISPLAY_NAMES = {
    "apple_watch": "Apple Watch / HealthKit",
    "google_fit": "Google Fit",
    "samsung_health": "Samsung Health",
    "garmin": "Garmin Connect"
}

DEVICE_ICONS = {
    "apple_watch": "⌚",
    "google_fit": "💚",
    "samsung_health": "💙",
    "garmin": "🟠"
}


def get_mock_activity_data():
    """Generate realistic mock wearable activity data."""
    activities = []
    for i in range(7):
        day = datetime.utcnow() - timedelta(days=i)
        if random.random() > 0.3:
            activities.append({
                "date": day.strftime("%b %d"),
                "type": random.choice(["Pilates Session", "Morning Walk", "Yoga", "Pilates Flow", "Stretching"]),
                "duration": random.randint(20, 55),
                "calories": random.randint(150, 400),
                "heart_rate_avg": random.randint(95, 135),
                "steps": random.randint(2000, 8000) if i > 0 else random.randint(6000, 12000)
            })
    return activities


@router.get("/wearables", response_class=HTMLResponse)
async def wearables_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    devices = db.query(models.WearableDevice).filter(
        models.WearableDevice.user_id == current_user.id
    ).all()

    mock_activities = get_mock_activity_data()

    # Mock stats
    total_steps = random.randint(45000, 80000)
    active_minutes = random.randint(180, 350)
    calories_week = random.randint(1800, 3200)
    avg_heart_rate = random.randint(62, 75)

    success = request.cookies.get("flash_success", "")
    response = templates.TemplateResponse("wearables/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "devices": devices,
        "device_display_names": DEVICE_DISPLAY_NAMES,
        "device_icons": DEVICE_ICONS,
        "mock_activities": mock_activities,
        "total_steps": total_steps,
        "active_minutes": active_minutes,
        "calories_week": calories_week,
        "avg_heart_rate": avg_heart_rate,
        "success": success
    })
    response.delete_cookie("flash_success")
    return response


@router.post("/wearables/connect")
async def connect_device(
    request: Request,
    device_type: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    existing = db.query(models.WearableDevice).filter(
        models.WearableDevice.user_id == current_user.id,
        models.WearableDevice.device_type == device_type
    ).first()

    if not existing:
        device_name = DEVICE_DISPLAY_NAMES.get(device_type, device_type)
        device = models.WearableDevice(
            user_id=current_user.id,
            device_type=device_type,
            device_name=device_name,
            is_active=True,
            connected_at=datetime.utcnow(),
            last_sync_at=datetime.utcnow()
        )
        db.add(device)
        db.commit()
    else:
        existing.is_active = True
        existing.last_sync_at = datetime.utcnow()
        db.commit()

    response = RedirectResponse(url="/wearables", status_code=302)
    response.set_cookie("flash_success", f"{DEVICE_DISPLAY_NAMES.get(device_type, device_type)} connected successfully!", max_age=10)
    return response


@router.post("/wearables/disconnect/{device_id}")
async def disconnect_device(
    request: Request,
    device_id: int,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    device = db.query(models.WearableDevice).filter(
        models.WearableDevice.id == device_id,
        models.WearableDevice.user_id == current_user.id
    ).first()

    if device:
        device.is_active = False
        db.commit()

    response = RedirectResponse(url="/wearables", status_code=302)
    response.set_cookie("flash_success", "Device disconnected.", max_age=10)
    return response


@router.get("/wearables/sync", response_class=HTMLResponse)
async def sync_wearables(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<div class="text-red-500">Not authenticated</div>')

    devices = db.query(models.WearableDevice).filter(
        models.WearableDevice.user_id == current_user.id,
        models.WearableDevice.is_active == True
    ).all()

    for device in devices:
        device.last_sync_at = datetime.utcnow()
    db.commit()

    activities = get_mock_activity_data()

    html_parts = []
    for a in activities[:5]:
        html_parts.append(f'''
            <div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-teal-100 rounded-xl flex items-center justify-center text-lg">🏃</div>
                    <div>
                        <div class="font-medium text-gray-800 text-sm">{a["type"]}</div>
                        <div class="text-xs text-gray-500">{a["date"]} • {a["duration"]} min</div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-semibold text-teal-600">{a["calories"]} cal</div>
                    <div class="text-xs text-gray-400">♥ {a["heart_rate_avg"]} bpm</div>
                </div>
            </div>
        ''')

    return HTMLResponse(f'''
        <div class="space-y-1">
            <div class="flex items-center gap-2 text-green-600 text-sm font-medium mb-3 p-2 bg-green-50 rounded-lg">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Synced {len(devices)} device(s) at {datetime.utcnow().strftime("%H:%M")}
            </div>
            {"".join(html_parts)}
        </div>
    ''')
