from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime
import json

from database import engine, Base, SessionLocal
import models
import auth

from routers import (
    auth_router,
    dashboard_router,
    videos_router,
    meal_plans_router,
    marketplace_router,
    equipment_router,
    wearables_router,
    profile_router,
    subscription_router
)

app = FastAPI(title="Forma Pilates Platform", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(videos_router.router)
app.include_router(meal_plans_router.router)
app.include_router(marketplace_router.router)
app.include_router(equipment_router.router)
app.include_router(wearables_router.router)
app.include_router(profile_router.router)
app.include_router(subscription_router.router)


def seed_database():
    """Seed the database with initial data if empty."""
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(models.User).count() > 0:
            return

        print("[SEED] Seeding database...")

        # Create demo user
        demo_user = models.User(
            email="demo@pilates.com",
            full_name="Sarah Johnson",
            password_hash=auth.hash_password("demo1234"),
            subscription_tier="premium",
            avatar_url="https://picsum.photos/seed/sarah/128/128",
            bio="Pilates enthusiast and wellness coach. Passionate about helping others achieve their fitness goals.",
            health_notes="No known allergies. Prefer low-impact exercises. Post-natal recovery phase complete.",
            height_cm=168.0,
            weight_kg=62.0,
            target_weight_kg=58.0,
            age=32
        )
        db.add(demo_user)
        db.flush()

        # Create premium subscription for demo user
        from datetime import timedelta
        sub = models.Subscription(
            user_id=demo_user.id,
            plan_type="premium",
            monthly_price=59.00,
            status="active",
            start_date=datetime.utcnow() - timedelta(days=45),
            renewal_date=datetime.utcnow() + timedelta(days=15)
        )
        db.add(sub)
        db.flush()

        # Seed 12 videos
        videos_data = [
            # Beginner - Mat
            {
                "title": "Morning Flow - Full Body Awakening",
                "description": "Start your day right with this gentle full-body flow. Perfect for beginners, this session focuses on controlled breathing, spinal articulation, and activating your core.",
                "duration_seconds": 1500,  # 25 min
                "difficulty_level": "beginner",
                "category": "mat",
                "instructor_name": "Emma Clarke",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video1/640/360",
                "tags": "morning,flow,full-body,breathing",
                "rating": 4.8,
                "is_premium": False,
                "view_count": 12450
            },
            # Beginner - Core
            {
                "title": "Core Strength Fundamentals",
                "description": "Build a solid foundation with this essential core workout. Learn proper engagement techniques, pelvic floor activation, and the fundamental pilates principles.",
                "duration_seconds": 1800,  # 30 min
                "difficulty_level": "beginner",
                "category": "core",
                "instructor_name": "Sarah Mitchell",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video2/640/360",
                "tags": "core,fundamentals,strength,pelvic-floor",
                "rating": 4.9,
                "is_premium": False,
                "view_count": 18920
            },
            # Beginner - Mat
            {
                "title": "Gentle Stretch & Mobility",
                "description": "Improve your flexibility and joint mobility with this gentle stretching session. Ideal for those new to pilates or returning after a break.",
                "duration_seconds": 1200,  # 20 min
                "difficulty_level": "beginner",
                "category": "flexibility",
                "instructor_name": "Emma Clarke",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video3/640/360",
                "tags": "stretch,mobility,flexibility,gentle",
                "rating": 4.7,
                "is_premium": False,
                "view_count": 9870
            },
            # Beginner - Mat
            {
                "title": "Breathwork & Mindful Movement",
                "description": "Connect breath to movement in this calming beginner session. Reduce stress, improve posture, and build body awareness through mindful pilates.",
                "duration_seconds": 1320,  # 22 min
                "difficulty_level": "beginner",
                "category": "mat",
                "instructor_name": "Dr. Lisa Chen",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video4/640/360",
                "tags": "breathwork,mindful,stress-relief,posture",
                "rating": 4.6,
                "is_premium": False,
                "view_count": 7650
            },
            # Intermediate - Reformer
            {
                "title": "Reformer Foundations",
                "description": "Your introduction to reformer pilates. Learn the machine, springs, and fundamental reformer exercises for total body toning.",
                "duration_seconds": 2400,  # 40 min
                "difficulty_level": "intermediate",
                "category": "reformer",
                "instructor_name": "Jade Williams",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video5/640/360",
                "tags": "reformer,toning,intermediate,machine",
                "rating": 4.8,
                "is_premium": True,
                "view_count": 6230
            },
            # Intermediate - Flexibility
            {
                "title": "Hip Opening & Spine Release",
                "description": "Target tight hips and compressed vertebrae with this intermediate flexibility session. Great for desk workers and those with lower back tension.",
                "duration_seconds": 2100,  # 35 min
                "difficulty_level": "intermediate",
                "category": "flexibility",
                "instructor_name": "Emma Clarke",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video6/640/360",
                "tags": "hips,spine,flexibility,back-pain",
                "rating": 4.9,
                "is_premium": False,
                "view_count": 15430
            },
            # Intermediate - Reformer
            {
                "title": "Reformer Cardio Flow",
                "description": "Get your heart rate up with this dynamic reformer session. Fluid transitions and challenging sequences build strength and endurance.",
                "duration_seconds": 2700,  # 45 min
                "difficulty_level": "intermediate",
                "category": "reformer",
                "instructor_name": "Jade Williams",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video7/640/360",
                "tags": "reformer,cardio,endurance,dynamic",
                "rating": 4.7,
                "is_premium": True,
                "view_count": 5890
            },
            # Intermediate - Core
            {
                "title": "Deep Core & Stability",
                "description": "Challenge your core stability with advanced breathing patterns, rotation work, and anti-gravity exercises. Build the deep stabilizers that protect your spine.",
                "duration_seconds": 2400,  # 40 min
                "difficulty_level": "intermediate",
                "category": "core",
                "instructor_name": "Sarah Mitchell",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video8/640/360",
                "tags": "deep-core,stability,spine,rotation",
                "rating": 4.8,
                "is_premium": False,
                "view_count": 11200
            },
            # Advanced - Reformer
            {
                "title": "Advanced Reformer Challenge",
                "description": "Push your limits with this demanding reformer workout. Includes jump board sequences, unilateral work, and complex spring configurations.",
                "duration_seconds": 3300,  # 55 min
                "difficulty_level": "advanced",
                "category": "reformer",
                "instructor_name": "Jade Williams",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video9/640/360",
                "tags": "advanced,reformer,challenge,jump-board",
                "rating": 4.9,
                "is_premium": True,
                "view_count": 4320
            },
            # Advanced - Core
            {
                "title": "Power Core - Elite Series",
                "description": "Elite-level core training for experienced pilates practitioners. Includes teaser variations, rolling like a ball, and advanced abdominal series.",
                "duration_seconds": 3000,  # 50 min
                "difficulty_level": "advanced",
                "category": "core",
                "instructor_name": "Sarah Mitchell",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video10/640/360",
                "tags": "advanced,core,elite,teaser",
                "rating": 4.8,
                "is_premium": True,
                "view_count": 3870
            },
            # Prenatal
            {
                "title": "Prenatal Pilates - Safe Pregnancy Workout",
                "description": "Stay strong and comfortable throughout your pregnancy with this specially designed program. Dr. Lisa Chen guides you through safe modifications for all trimesters.",
                "duration_seconds": 2100,  # 35 min
                "difficulty_level": "beginner",
                "category": "prenatal",
                "instructor_name": "Dr. Lisa Chen",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video11/640/360",
                "tags": "prenatal,pregnancy,safe,trimesters",
                "rating": 4.9,
                "is_premium": True,
                "view_count": 8910
            },
            # Postnatal
            {
                "title": "Post-Natal Recovery Program",
                "description": "Safely rebuild strength after childbirth. This expert-guided program heals diastasis recti, reconnects pelvic floor, and gradually restores your strength.",
                "duration_seconds": 1800,  # 30 min
                "difficulty_level": "beginner",
                "category": "postnatal",
                "instructor_name": "Dr. Lisa Chen",
                "video_url": "https://www.youtube.com/embed/g_tea8ZNk5A",
                "thumbnail_url": "https://picsum.photos/seed/video12/640/360",
                "tags": "postnatal,recovery,diastasis,pelvic-floor",
                "rating": 4.9,
                "is_premium": True,
                "view_count": 7240
            }
        ]

        for v_data in videos_data:
            video = models.Video(**v_data)
            db.add(video)

        # Seed 8 Products
        products_data = [
            {
                "name": "Pilates Resistance Bands Set",
                "description": "Professional-grade resistance bands in 3 strengths (light, medium, heavy). Perfect for reformer simulation and strength training at home.",
                "price": 24.99,
                "stock_quantity": 150,
                "category": "Equipment",
                "image_url": "https://picsum.photos/seed/prod1/400/400",
                "tags": "resistance,bands,strength,home",
                "sales_count": 324
            },
            {
                "name": "Premium Yoga & Pilates Mat",
                "description": "6mm thick non-slip mat with alignment lines. Eco-friendly TPE material, sweat-resistant, with carry strap included.",
                "price": 49.99,
                "stock_quantity": 80,
                "category": "Equipment",
                "image_url": "https://picsum.photos/seed/prod2/400/400",
                "tags": "mat,non-slip,eco,alignment",
                "sales_count": 218
            },
            {
                "name": "Pilates Circle / Magic Ring",
                "description": "Classic pilates toning ring for inner thigh, core, and upper body work. Flexible yet firm, with padded handles for comfort.",
                "price": 29.99,
                "stock_quantity": 95,
                "category": "Equipment",
                "image_url": "https://picsum.photos/seed/prod3/400/400",
                "tags": "ring,circle,toning,inner-thigh",
                "sales_count": 156
            },
            {
                "name": "High-Density Foam Roller",
                "description": "Full-length 90cm foam roller for myofascial release, balance training, and spinal mobility. Supports up to 300lbs.",
                "price": 34.99,
                "stock_quantity": 60,
                "category": "Equipment",
                "image_url": "https://picsum.photos/seed/prod4/400/400",
                "tags": "foam-roller,recovery,balance,mobility",
                "sales_count": 189
            },
            {
                "name": "Forma Grip Socks (2-Pack)",
                "description": "Non-slip pilates grip socks with individual toe pockets for maximum grip and hygiene. Available in S/M/L. Includes 2 pairs.",
                "price": 18.99,
                "stock_quantity": 200,
                "category": "Apparel",
                "image_url": "https://picsum.photos/seed/prod5/400/400",
                "tags": "socks,grip,non-slip,hygiene",
                "sales_count": 445
            },
            {
                "name": "Forma Branded Water Bottle",
                "description": "Double-wall insulated 750ml stainless steel bottle. Keeps water cold 24hrs or warm 12hrs. Leak-proof lid with measurement markings.",
                "price": 22.99,
                "stock_quantity": 120,
                "category": "Accessories",
                "image_url": "https://picsum.photos/seed/prod6/400/400",
                "tags": "water-bottle,insulated,stainless-steel,branded",
                "sales_count": 267
            },
            {
                "name": "Wellness & Workout Journal",
                "description": "Beautifully designed 90-day workout and wellness tracker. Includes habit tracker, meal log, body measurements, and reflections.",
                "price": 16.99,
                "stock_quantity": 75,
                "category": "Accessories",
                "image_url": "https://picsum.photos/seed/prod7/400/400",
                "tags": "journal,tracker,wellness,habit",
                "sales_count": 132
            },
            {
                "name": "Yoga & Pilates Stretching Strap",
                "description": "8ft nylon stretching strap with 12 loops for precise positioning. Improves flexibility, great for rehab and advanced stretch work.",
                "price": 14.99,
                "stock_quantity": 180,
                "category": "Equipment",
                "image_url": "https://picsum.photos/seed/prod8/400/400",
                "tags": "strap,stretching,flexibility,rehab",
                "sales_count": 198
            }
        ]

        for p_data in products_data:
            product = models.Product(**p_data)
            db.add(product)

        # Create some workout sessions for demo user
        db.flush()
        videos = db.query(models.Video).limit(5).all()
        from datetime import timedelta
        for i, video in enumerate(videos[:3]):
            session = models.WorkoutSession(
                user_id=demo_user.id,
                video_id=video.id,
                duration_completed_seconds=video.duration_seconds,
                calories_burned=round(video.duration_seconds / 60 * 5.5),
                started_at=datetime.utcnow() - timedelta(days=i+1),
                completed_at=datetime.utcnow() - timedelta(days=i+1, minutes=-int(video.duration_seconds/60))
            )
            db.add(session)

        db.commit()
        print("[SEED] Database seeded successfully!")
        print("[SEED] Demo user: demo@pilates.com / demo1234")

    except Exception as e:
        print(f"[SEED ERROR] {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    seed_database()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    db = SessionLocal()
    try:
        current_user = auth.get_current_user_optional(request)
        if current_user:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "current_user": current_user,
                "is_premium": current_user.subscription_tier == "premium"
            })

        sample_videos = db.query(models.Video).filter(
            models.Video.is_premium == False
        ).limit(4).all()

        def fmt_dur(s):
            m = s // 60
            return f"{m} min"

        for v in sample_videos:
            v.formatted_duration = fmt_dur(v.duration_seconds)

        success = request.cookies.get("flash_success", "")
        response = templates.TemplateResponse("index.html", {
            "request": request,
            "current_user": None,
            "is_premium": False,
            "sample_videos": sample_videos,
            "success": success
        })
        response.delete_cookie("flash_success")
        return response
    finally:
        db.close()


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    current_user = auth.get_current_user_optional(request)
    return templates.TemplateResponse("errors/404.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium" if current_user else False
    }, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    current_user = auth.get_current_user_optional(request)
    return templates.TemplateResponse("errors/500.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": False
    }, status_code=500)
