# Forma Pilates Platform

A full-stack online pilates subscription platform built with Python (FastAPI), featuring AI-powered meal planning, wearable device sync, equipment loan management, and a branded marketplace.

## Tech Stack

- **Backend:** FastAPI (Python) + Uvicorn
- **Templates:** Jinja2 (server-side HTML)
- **Styling:** Tailwind CSS + custom CSS
- **Interactivity:** Alpine.js + HTMX
- **Database:** SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT via HTTP-only cookies (python-jose + passlib/bcrypt)
- **AI Meal Plans:** Anthropic Claude API
- **Payments:** Stripe
- **Shipping:** Shippo API

## Features

| Feature | Basic ($39/mo) | Premium ($59/mo) |
|---|---|---|
| 200+ pilates video library | ✓ | ✓ |
| Progress tracking & streaks | ✓ | ✓ |
| Marketplace access | ✓ | ✓ |
| AI-powered meal plans (Claude) | — | ✓ |
| Wearable device sync | — | ✓ |
| $200 equipment kit included | — | ✓ |
| Post-natal specialist programs | — | ✓ |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (optional — works without API keys)
cp .env.example .env
# Edit .env with your API keys (Stripe, Anthropic, etc.)

# 3. Run the server
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`

**Demo login:** `demo@pilates.com` / `demo1234` (Premium account, seeded automatically)

## Project Structure

```
platform/
├── main.py                  # FastAPI app, startup seeding
├── models.py                # SQLAlchemy models
├── auth.py                  # JWT auth, password hashing
├── database.py              # DB engine & session
├── config.py                # Settings from .env
├── requirements.txt
├── routers/
│   ├── auth_router.py       # Login, register, logout
│   ├── dashboard_router.py  # Dashboard stats
│   ├── videos_router.py     # Video library + player
│   ├── meal_plans_router.py # AI meal plan generation
│   ├── marketplace_router.py# Shop + cart + checkout
│   ├── equipment_router.py  # Equipment loan tracking
│   ├── wearables_router.py  # Device connect/sync
│   ├── profile_router.py    # User profile management
│   └── subscription_router.py # Plan upgrade/cancel
├── templates/
│   ├── base.html            # Nav, footer, flash messages
│   ├── index.html           # Landing page
│   ├── auth/                # Login & register
│   ├── dashboard/           # Member dashboard
│   ├── videos/              # Library + player + HTMX grid
│   ├── meal_plans/          # AI meal plan UI
│   ├── marketplace/         # Shop + cart + order success
│   ├── equipment/           # Kit status + timeline
│   ├── wearables/           # Device management
│   ├── profile/             # Account settings
│   ├── subscription/        # Plan management
│   └── errors/              # 404 + 500 pages
└── static/
    ├── css/custom.css       # Custom styles, badges, animations
    └── js/app.js            # Minimal vanilla JS helpers
```

## Environment Variables

```env
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL=sqlite:///./pilates.db
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
ANTHROPIC_API_KEY=sk-ant-...
```

All API keys are optional — the platform falls back to mock data gracefully.

## Colour Palette

| Name | Hex |
|---|---|
| Navy | `#21295C` |
| Dark Blue | `#065A82` |
| Medium Blue | `#1C7293` |
| Teal | `#028090` |
| Bright Teal | `#00A896` |
