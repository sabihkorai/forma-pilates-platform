from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

import models
import auth
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

VIDEOS_PER_PAGE = 9


def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    if minutes >= 60:
        h = minutes // 60
        m = minutes % 60
        return f"{h}h {m}m"
    return f"{minutes} min"


@router.get("/videos", response_class=HTMLResponse)
async def videos_list(
    request: Request,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    duration_filter: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    query = db.query(models.Video)

    if category and category != "all":
        query = query.filter(models.Video.category == category)
    if difficulty and difficulty != "all":
        query = query.filter(models.Video.difficulty_level == difficulty)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            models.Video.title.ilike(search_term) |
            models.Video.description.ilike(search_term) |
            models.Video.instructor_name.ilike(search_term)
        )
    if duration_filter and duration_filter != "any":
        if duration_filter == "under20":
            query = query.filter(models.Video.duration_seconds < 1200)
        elif duration_filter == "20to30":
            query = query.filter(models.Video.duration_seconds.between(1200, 1800))
        elif duration_filter == "30to45":
            query = query.filter(models.Video.duration_seconds.between(1800, 2700))
        elif duration_filter == "45plus":
            query = query.filter(models.Video.duration_seconds >= 2700)

    total = query.count()
    offset = (page - 1) * VIDEOS_PER_PAGE
    videos = query.order_by(models.Video.published_at.desc()).offset(offset).limit(VIDEOS_PER_PAGE).all()

    total_pages = (total + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE

    for v in videos:
        v.formatted_duration = format_duration(v.duration_seconds)

    is_htmx = request.headers.get("HX-Request")

    context = {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "videos": videos,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "category": category or "all",
        "difficulty": difficulty or "all",
        "search": search or "",
        "duration_filter": duration_filter or "any",
    }

    if is_htmx:
        return templates.TemplateResponse("videos/_grid.html", context)

    return templates.TemplateResponse("videos/index.html", context)


@router.get("/videos/filter", response_class=HTMLResponse)
async def videos_filter(
    request: Request,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    duration_filter: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    query = db.query(models.Video)

    if category and category != "all":
        query = query.filter(models.Video.category == category)
    if difficulty and difficulty != "all":
        query = query.filter(models.Video.difficulty_level == difficulty)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            models.Video.title.ilike(search_term) |
            models.Video.description.ilike(search_term) |
            models.Video.instructor_name.ilike(search_term)
        )
    if duration_filter and duration_filter != "any":
        if duration_filter == "under20":
            query = query.filter(models.Video.duration_seconds < 1200)
        elif duration_filter == "20to30":
            query = query.filter(models.Video.duration_seconds.between(1200, 1800))
        elif duration_filter == "30to45":
            query = query.filter(models.Video.duration_seconds.between(1800, 2700))
        elif duration_filter == "45plus":
            query = query.filter(models.Video.duration_seconds >= 2700)

    total = query.count()
    offset = (page - 1) * VIDEOS_PER_PAGE
    videos = query.order_by(models.Video.published_at.desc()).offset(offset).limit(VIDEOS_PER_PAGE).all()
    total_pages = (total + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE

    for v in videos:
        v.formatted_duration = format_duration(v.duration_seconds)

    return templates.TemplateResponse("videos/_grid.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "videos": videos,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "category": category or "all",
        "difficulty": difficulty or "all",
        "search": search or "",
        "duration_filter": duration_filter or "any",
    })


@router.get("/videos/{video_id}", response_class=HTMLResponse)
async def video_player(
    request: Request,
    video_id: int,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        return RedirectResponse(url="/videos", status_code=302)

    # Premium gate
    if video.is_premium and current_user.subscription_tier != "premium":
        return templates.TemplateResponse("videos/player.html", {
            "request": request,
            "current_user": current_user,
            "is_premium": False,
            "video": video,
            "locked": True,
            "related_videos": [],
            "session": None,
            "formatted_duration": format_duration(video.duration_seconds)
        })

    # Increment view count
    video.view_count = (video.view_count or 0) + 1
    db.commit()

    # Create or get workout session
    session = db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == current_user.id,
        models.WorkoutSession.video_id == video_id,
        models.WorkoutSession.completed_at == None
    ).first()

    if not session:
        session = models.WorkoutSession(
            user_id=current_user.id,
            video_id=video_id,
            started_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Related videos
    related = db.query(models.Video).filter(
        models.Video.id != video_id,
        models.Video.category == video.category
    ).limit(3).all()

    if len(related) < 3:
        more = db.query(models.Video).filter(
            models.Video.id != video_id
        ).limit(3 - len(related)).all()
        related.extend(more)

    for v in related:
        v.formatted_duration = format_duration(v.duration_seconds)

    return templates.TemplateResponse("videos/player.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "video": video,
        "locked": False,
        "related_videos": related,
        "session": session,
        "formatted_duration": format_duration(video.duration_seconds)
    })


@router.post("/videos/{video_id}/complete", response_class=HTMLResponse)
async def complete_video(
    request: Request,
    video_id: int,
    notes: str = Form(default=""),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<div class="text-red-500">Not authenticated</div>')

    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        return HTMLResponse('<div class="text-red-500">Video not found</div>')

    session = db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == current_user.id,
        models.WorkoutSession.video_id == video_id,
        models.WorkoutSession.completed_at == None
    ).first()

    if not session:
        session = models.WorkoutSession(
            user_id=current_user.id,
            video_id=video_id,
            started_at=datetime.utcnow()
        )
        db.add(session)

    session.completed_at = datetime.utcnow()
    session.duration_completed_seconds = video.duration_seconds
    session.calories_burned = round(video.duration_seconds / 60 * 5.5)
    session.notes = notes

    db.commit()

    return HTMLResponse('''
        <div class="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
            <div class="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
            </div>
            <div>
                <p class="font-semibold text-green-800">Workout Complete!</p>
                <p class="text-sm text-green-600">Great work! This session has been saved to your history.</p>
            </div>
        </div>
    ''')
