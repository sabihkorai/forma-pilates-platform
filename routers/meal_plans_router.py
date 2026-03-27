from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import json
from typing import Optional

import models
import auth
from database import get_db
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_mock_meal_plan(goal: str, dietary_preference: str, calories: int) -> dict:
    """Return a realistic mock meal plan."""
    return {
        "days": {
            "Monday": {
                "breakfast": "Greek yogurt parfait with berries, granola, and honey (350 cal)",
                "lunch": "Grilled chicken quinoa bowl with roasted vegetables and tahini dressing (520 cal)",
                "dinner": "Baked salmon with steamed broccoli and brown rice (480 cal)",
                "snacks": "Apple with almond butter, handful of mixed nuts (250 cal)"
            },
            "Tuesday": {
                "breakfast": "Overnight oats with chia seeds, banana, and almond milk (380 cal)",
                "lunch": "Turkey and avocado wrap with mixed greens and tomato (490 cal)",
                "dinner": "Stir-fried tofu with vegetables and soba noodles (450 cal)",
                "snacks": "Hummus with cucumber and carrot sticks, orange (220 cal)"
            },
            "Wednesday": {
                "breakfast": "Spinach and mushroom omelette with whole grain toast (400 cal)",
                "lunch": "Lentil soup with crusty sourdough and side salad (510 cal)",
                "dinner": "Grilled chicken breast with sweet potato mash and green beans (460 cal)",
                "snacks": "Protein smoothie with banana and peanut butter (280 cal)"
            },
            "Thursday": {
                "breakfast": "Acai bowl with fresh fruit, coconut flakes, and pumpkin seeds (420 cal)",
                "lunch": "Mediterranean salad with feta, olives, chickpeas, and grilled veggies (480 cal)",
                "dinner": "Lean beef stir-fry with bell peppers, broccoli, and jasmine rice (500 cal)",
                "snacks": "Rice cakes with avocado and cherry tomatoes (200 cal)"
            },
            "Friday": {
                "breakfast": "Whole grain pancakes with fresh berries and maple syrup (390 cal)",
                "lunch": "Tuna salad stuffed bell peppers with quinoa (470 cal)",
                "dinner": "Baked cod with asparagus, lemon, and herb roasted potatoes (440 cal)",
                "snacks": "Cottage cheese with pineapple, dark chocolate square (240 cal)"
            },
            "Saturday": {
                "breakfast": "Smashed avocado toast with poached eggs and microgreens (430 cal)",
                "lunch": "Chicken and vegetable soup with whole grain bread (460 cal)",
                "dinner": "Grilled shrimp tacos with mango salsa and cabbage slaw (490 cal)",
                "snacks": "Trail mix with dried cranberries, seeds, and nuts (260 cal)"
            },
            "Sunday": {
                "breakfast": "Veggie frittata with goat cheese, sun-dried tomatoes, and spinach (410 cal)",
                "lunch": "Roasted vegetable and hummus grain bowl (500 cal)",
                "dinner": "Herb-crusted pork tenderloin with roasted root vegetables (470 cal)",
                "snacks": "Edamame with sea salt, fresh fruit salad (230 cal)"
            }
        },
        "macros": {
            "protein_g": 125,
            "carbs_g": 195,
            "fat_g": 62
        },
        "shopping_list": [
            "Greek yogurt (plain, full-fat)", "Mixed berries (fresh or frozen)", "Granola (low sugar)",
            "Chicken breast (1.5 kg)", "Salmon fillets (4 portions)", "Lean beef (500g)",
            "Cod fillets (4 portions)", "Tuna (canned, 3 tins)", "Shrimp (500g)",
            "Quinoa (500g)", "Brown rice (1 kg)", "Soba noodles (250g)",
            "Sweet potatoes (4 medium)", "Mixed salad greens", "Spinach (large bag)",
            "Broccoli (2 heads)", "Asparagus (1 bunch)", "Bell peppers (6 mixed)",
            "Cherry tomatoes", "Cucumber (2)", "Avocados (4)",
            "Lemons (4)", "Banana (6)", "Apples (6)",
            "Almonds and mixed nuts (200g)", "Almond butter", "Chia seeds",
            "Olive oil", "Tahini", "Hummus (store-bought or homemade ingredients)",
            "Eggs (12)", "Feta cheese (150g)", "Cottage cheese (500g)",
            "Whole grain bread loaf", "Rice cakes", "Oats (500g)"
        ]
    }


@router.get("/meal-plans", response_class=HTMLResponse)
async def meal_plans_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    saved_plans = (
        db.query(models.MealPlan)
        .filter(
            models.MealPlan.user_id == current_user.id,
            models.MealPlan.is_saved == True
        )
        .order_by(models.MealPlan.generated_at.desc())
        .limit(3)
        .all()
    )

    return templates.TemplateResponse("meal_plans/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "saved_plans": saved_plans
    })


@router.post("/meal-plans/generate", response_class=HTMLResponse)
async def generate_meal_plan(
    request: Request,
    age: int = Form(default=30),
    weight: float = Form(default=65.0),
    height: float = Form(default=165.0),
    goal: str = Form(default="maintenance"),
    dietary_preference: str = Form(default="none"),
    restrictions: str = Form(default=""),
    calories: int = Form(default=1800),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<div class="text-red-500 p-4">Not authenticated. Please log in.</div>')

    if current_user.subscription_tier != "premium":
        return HTMLResponse('''
            <div class="text-center py-12">
                <div class="text-6xl mb-4">🔒</div>
                <h3 class="text-xl font-bold text-gray-800 mb-2">Premium Feature</h3>
                <p class="text-gray-600 mb-4">AI Meal Plans are available with Premium subscription.</p>
                <a href="/subscription" class="btn-primary px-6 py-3 rounded-xl font-semibold">Upgrade to Premium</a>
            </div>
        ''')

    meal_data = None

    # Try Anthropic API if key is configured
    if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "your_anthropic_api_key":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            prompt = f"""Create a personalized weekly meal plan for:
- Age: {age}, Weight: {weight}kg, Height: {height}cm
- Goal: {goal}
- Dietary preference: {dietary_preference}
- Allergies/restrictions: {restrictions if restrictions else 'None'}
- Daily calorie target: {calories} calories

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "days": {{
    "Monday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}},
    "Tuesday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}},
    "Wednesday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}},
    "Thursday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}},
    "Friday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}},
    "Saturday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}},
    "Sunday": {{"breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}}
  }},
  "macros": {{"protein_g": 120, "carbs_g": 180, "fat_g": 60}},
  "shopping_list": ["item1", "item2", "item3"]
}}"""

            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text.strip()
            # Extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            meal_data = json.loads(response_text)
        except Exception as e:
            print(f"[ANTHROPIC ERROR] {e} - falling back to mock data")
            meal_data = get_mock_meal_plan(goal, dietary_preference, calories)
    else:
        meal_data = get_mock_meal_plan(goal, dietary_preference, calories)

    # Save to DB
    plan = models.MealPlan(
        user_id=current_user.id,
        meals_data=json.dumps(meal_data.get("days", {})),
        macros=json.dumps(meal_data.get("macros", {})),
        shopping_list=json.dumps(meal_data.get("shopping_list", [])),
        dietary_preferences=dietary_preference,
        health_goals=goal,
        restrictions=restrictions,
        is_saved=False,
        generated_at=datetime.utcnow()
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    macros = meal_data.get("macros", {})
    days = meal_data.get("days", {})
    shopping_list = meal_data.get("shopping_list", [])

    total_macros = (macros.get("protein_g", 0) + macros.get("carbs_g", 0) + macros.get("fat_g", 0)) or 1
    protein_pct = round(macros.get("protein_g", 0) / total_macros * 100)
    carbs_pct = round(macros.get("carbs_g", 0) / total_macros * 100)
    fat_pct = round(macros.get("fat_g", 0) / total_macros * 100)

    days_html = ""
    day_colors = {
        "Monday": "bg-blue-50 border-blue-200",
        "Tuesday": "bg-teal-50 border-teal-200",
        "Wednesday": "bg-green-50 border-green-200",
        "Thursday": "bg-purple-50 border-purple-200",
        "Friday": "bg-pink-50 border-pink-200",
        "Saturday": "bg-orange-50 border-orange-200",
        "Sunday": "bg-yellow-50 border-yellow-200"
    }
    for day, meals in days.items():
        color = day_colors.get(day, "bg-gray-50 border-gray-200")
        days_html += f'''
        <div class="border {color} rounded-xl p-4">
            <h4 class="font-bold text-gray-800 mb-3 text-sm uppercase tracking-wide">{day}</h4>
            <div class="space-y-2 text-sm">
                <div><span class="font-medium text-orange-600">🌅 Breakfast:</span> <span class="text-gray-700">{meals.get("breakfast", "")}</span></div>
                <div><span class="font-medium text-yellow-600">☀️ Lunch:</span> <span class="text-gray-700">{meals.get("lunch", "")}</span></div>
                <div><span class="font-medium text-purple-600">🌙 Dinner:</span> <span class="text-gray-700">{meals.get("dinner", "")}</span></div>
                <div><span class="font-medium text-green-600">🍎 Snacks:</span> <span class="text-gray-700">{meals.get("snacks", "")}</span></div>
            </div>
        </div>'''

    shopping_items = "".join(f'<li class="flex items-center gap-2"><input type="checkbox" class="rounded text-teal-500"><span>{item}</span></li>' for item in shopping_list)

    html = f'''
    <div class="space-y-6" id="meal-plan-result">
        <div class="flex items-center justify-between">
            <h3 class="text-xl font-bold text-gray-900">Your Personalized Meal Plan</h3>
            <div class="flex gap-2">
                <form hx-post="/meal-plans/{plan.id}/save" hx-swap="none" hx-on::after-request="this.querySelector('button').textContent='Saved ✓'">
                    <button type="submit" class="px-4 py-2 bg-teal-500 text-white rounded-xl text-sm font-medium hover:bg-teal-600 transition-colors">Save Plan</button>
                </form>
                <button onclick="document.getElementById('generate-form').scrollIntoView({{behavior:'smooth'}})" class="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">Regenerate</button>
            </div>
        </div>

        <!-- Macros Summary -->
        <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <h4 class="font-semibold text-gray-800 mb-4">Daily Macros</h4>
            <div class="grid grid-cols-3 gap-4 mb-4">
                <div class="text-center p-3 bg-blue-50 rounded-xl">
                    <div class="text-2xl font-bold text-blue-600">{macros.get("protein_g", 0)}g</div>
                    <div class="text-xs text-gray-500 mt-1">Protein</div>
                </div>
                <div class="text-center p-3 bg-green-50 rounded-xl">
                    <div class="text-2xl font-bold text-green-600">{macros.get("carbs_g", 0)}g</div>
                    <div class="text-xs text-gray-500 mt-1">Carbs</div>
                </div>
                <div class="text-center p-3 bg-yellow-50 rounded-xl">
                    <div class="text-2xl font-bold text-yellow-600">{macros.get("fat_g", 0)}g</div>
                    <div class="text-xs text-gray-500 mt-1">Fat</div>
                </div>
            </div>
            <div class="space-y-2">
                <div>
                    <div class="flex justify-between text-xs text-gray-500 mb-1"><span>Protein</span><span>{protein_pct}%</span></div>
                    <div class="h-2 bg-gray-100 rounded-full"><div class="h-2 bg-blue-500 rounded-full" style="width:{protein_pct}%"></div></div>
                </div>
                <div>
                    <div class="flex justify-between text-xs text-gray-500 mb-1"><span>Carbohydrates</span><span>{carbs_pct}%</span></div>
                    <div class="h-2 bg-gray-100 rounded-full"><div class="h-2 bg-green-500 rounded-full" style="width:{carbs_pct}%"></div></div>
                </div>
                <div>
                    <div class="flex justify-between text-xs text-gray-500 mb-1"><span>Fat</span><span>{fat_pct}%</span></div>
                    <div class="h-2 bg-gray-100 rounded-full"><div class="h-2 bg-yellow-500 rounded-full" style="width:{fat_pct}%"></div></div>
                </div>
            </div>
        </div>

        <!-- Weekly Calendar -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {days_html}
        </div>

        <!-- Shopping List -->
        <div x-data="{{open: false}}" class="bg-white border border-gray-200 rounded-xl shadow-sm">
            <button @click="open = !open" class="w-full flex items-center justify-between p-5 text-left">
                <h4 class="font-semibold text-gray-800">🛒 Shopping List ({len(shopping_list)} items)</h4>
                <svg :class="open ? 'rotate-180' : ''" class="w-5 h-5 text-gray-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
            </button>
            <div x-show="open" class="px-5 pb-5">
                <ul class="space-y-2 text-sm text-gray-700 columns-2">
                    {shopping_items}
                </ul>
            </div>
        </div>
    </div>
    '''
    return HTMLResponse(html)


@router.post("/meal-plans/{plan_id}/save", response_class=HTMLResponse)
async def save_meal_plan(
    request: Request,
    plan_id: int,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<div class="text-red-500">Not authenticated</div>')

    plan = db.query(models.MealPlan).filter(
        models.MealPlan.id == plan_id,
        models.MealPlan.user_id == current_user.id
    ).first()

    if plan:
        plan.is_saved = True
        db.commit()

    return HTMLResponse('<span>Saved ✓</span>')


@router.get("/meal-plans/{plan_id}", response_class=HTMLResponse)
async def view_meal_plan(
    request: Request,
    plan_id: int,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    plan = db.query(models.MealPlan).filter(
        models.MealPlan.id == plan_id,
        models.MealPlan.user_id == current_user.id
    ).first()

    if not plan:
        return RedirectResponse(url="/meal-plans", status_code=302)

    meals_data = json.loads(plan.meals_data or "{}")
    macros = json.loads(plan.macros or "{}")
    shopping_list = json.loads(plan.shopping_list or "[]")

    return templates.TemplateResponse("meal_plans/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "saved_plans": [plan],
        "view_plan": plan,
        "view_meals": meals_data,
        "view_macros": macros,
        "view_shopping": shopping_list
    })
