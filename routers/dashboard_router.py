from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

import models
import auth
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    # Fetch recent workout sessions
    recent_sessions = (
        db.query(models.WorkoutSession)
        .filter(models.WorkoutSession.user_id == current_user.id)
        .order_by(models.WorkoutSession.started_at.desc())
        .limit(5)
        .all()
    )

    # Stats for this week
    week_start = datetime.utcnow() - timedelta(days=7)
    weekly_sessions = (
        db.query(models.WorkoutSession)
        .filter(
            models.WorkoutSession.user_id == current_user.id,
            models.WorkoutSession.started_at >= week_start
        )
        .all()
    )

    videos_this_week = len(weekly_sessions)
    calories_burned = sum(s.calories_burned or 0 for s in weekly_sessions)
    total_workouts = db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == current_user.id
    ).count()

    # Calculate streak (simplified)
    streak_days = min(len(weekly_sessions), 7)

    # Get subscription info
    subscription = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == current_user.id,
            models.Subscription.status == "active"
        )
        .first()
    )

    # Get featured videos for "continue watching"
    featured_videos = db.query(models.Video).filter(
        models.Video.is_premium == False
    ).limit(3).all()
    if len(featured_videos) < 3:
        more_videos = db.query(models.Video).limit(3).all()
        featured_videos = more_videos

    # Build weekly activity data (Mon-Sun)
    today = datetime.utcnow()
    week_days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sessions = [
            s for s in weekly_sessions
            if s.started_at.date() == day.date()
        ]
        week_days.append({
            "name": day.strftime("%a"),
            "date": day.strftime("%m/%d"),
            "count": len(day_sessions),
            "active": len(day_sessions) > 0
        })

    # Recent meal plan
    meal_plan = None
    if current_user.subscription_tier == "premium":
        meal_plan = (
            db.query(models.MealPlan)
            .filter(
                models.MealPlan.user_id == current_user.id,
                models.MealPlan.is_saved == True
            )
            .order_by(models.MealPlan.generated_at.desc())
            .first()
        )

    # Equipment loan
    equipment_loan = None
    if current_user.subscription_tier == "premium":
        equipment_loan = (
            db.query(models.EquipmentLoan)
            .filter(models.EquipmentLoan.user_id == current_user.id)
            .first()
        )

    # Wearables
    wearable_count = db.query(models.WearableDevice).filter(
        models.WearableDevice.user_id == current_user.id,
        models.WearableDevice.is_active == True
    ).count()

    success_msg = request.cookies.get("flash_success", "")
    response = templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "recent_sessions": recent_sessions,
        "videos_this_week": videos_this_week,
        "streak_days": streak_days,
        "calories_burned": round(calories_burned),
        "total_workouts": total_workouts,
        "subscription": subscription,
        "featured_videos": featured_videos,
        "week_days": week_days,
        "meal_plan": meal_plan,
        "equipment_loan": equipment_loan,
        "wearable_count": wearable_count,
        "success": success_msg
    })
    response.delete_cookie("flash_success")
    return response
