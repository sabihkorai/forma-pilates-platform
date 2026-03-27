from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

import models
import auth
from database import get_db
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/marketplace", response_class=HTMLResponse)
async def marketplace(
    request: Request,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    query = db.query(models.Product)
    if category and category != "all":
        query = query.filter(models.Product.category == category)

    products = query.all()

    cart_count = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).count()

    categories = db.query(models.Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    success = request.cookies.get("flash_success", "")
    response = templates.TemplateResponse("marketplace/index.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "products": products,
        "cart_count": cart_count,
        "categories": categories,
        "selected_category": category or "all",
        "success": success
    })
    response.delete_cookie("flash_success")
    return response


@router.post("/marketplace/cart/add", response_class=HTMLResponse)
async def add_to_cart(
    request: Request,
    product_id: int = Form(...),
    quantity: int = Form(default=1),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<button class="btn-primary px-4 py-2 rounded-xl text-sm">Login to add</button>')

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return HTMLResponse('<span class="text-red-500 text-sm">Product not found</span>')

    cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == product_id
    ).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = models.CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.add(cart_item)

    db.commit()

    cart_count = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).count()

    return HTMLResponse(f'''
        <div class="flex items-center gap-2">
            <div class="flex items-center gap-1 text-green-600 text-sm font-medium">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Added to cart!
            </div>
            <span id="cart-count" class="ml-2 bg-teal-500 text-white text-xs rounded-full px-2 py-0.5">{cart_count}</span>
        </div>
    ''')


@router.get("/marketplace/cart", response_class=HTMLResponse)
async def cart_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    cart_items = (
        db.query(models.CartItem)
        .filter(models.CartItem.user_id == current_user.id)
        .all()
    )

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    tax = round(subtotal * 0.08, 2)
    shipping = 5.99 if subtotal < 50 else 0.0
    total = round(subtotal + tax + shipping, 2)

    return templates.TemplateResponse("marketplace/cart.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "cart_items": cart_items,
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "stripe_key": settings.STRIPE_PUBLISHABLE_KEY
    })


@router.post("/marketplace/cart/update", response_class=HTMLResponse)
async def update_cart(
    request: Request,
    cart_item_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<span class="text-red-500">Not authenticated</span>')

    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == cart_item_id,
        models.CartItem.user_id == current_user.id
    ).first()

    if cart_item:
        if quantity <= 0:
            db.delete(cart_item)
        else:
            cart_item.quantity = quantity
        db.commit()

    return RedirectResponse(url="/marketplace/cart", status_code=302)


@router.post("/marketplace/cart/remove", response_class=HTMLResponse)
async def remove_from_cart(
    request: Request,
    cart_item_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return HTMLResponse('<span class="text-red-500">Not authenticated</span>')

    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == cart_item_id,
        models.CartItem.user_id == current_user.id
    ).first()

    if cart_item:
        db.delete(cart_item)
        db.commit()

    return RedirectResponse(url="/marketplace/cart", status_code=302)


@router.post("/marketplace/checkout")
async def checkout(
    request: Request,
    shipping_address: str = Form(default=""),
    db: Session = Depends(get_db)
):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    cart_items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()

    if not cart_items:
        return RedirectResponse(url="/marketplace/cart", status_code=302)

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    tax = round(subtotal * 0.08, 2)
    shipping_cost = 5.99 if subtotal < 50 else 0.0
    total = round(subtotal + tax + shipping_cost, 2)

    # If Stripe key is configured, use real Stripe
    if settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"):
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            line_items = []
            for item in cart_items:
                line_items.append({
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": item.product.name},
                        "unit_amount": int(item.product.price * 100)
                    },
                    "quantity": item.quantity
                })

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=str(request.base_url) + "marketplace/order-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=str(request.base_url) + "marketplace/cart"
            )
            return RedirectResponse(url=session.url, status_code=303)
        except Exception as e:
            print(f"[STRIPE ERROR] {e}")

    # Mock checkout - create order directly
    order = models.Order(
        user_id=current_user.id,
        stripe_order_id=f"mock_order_{datetime.utcnow().timestamp()}",
        status="paid",
        subtotal=subtotal,
        tax=tax,
        shipping_cost=shipping_cost,
        total=total,
        shipping_address=shipping_address,
        paid_at=datetime.utcnow()
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        order_item = models.OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.product.price,
            subtotal=item.product.price * item.quantity
        )
        db.add(order_item)
        item.product.sales_count = (item.product.sales_count or 0) + item.quantity

    # Clear cart
    for item in cart_items:
        db.delete(item)

    db.commit()

    print(f"[EMAIL] Order confirmation sent to {current_user.email} - Order #{order.id}, Total: ${total}")

    response = RedirectResponse(url="/marketplace/order-success", status_code=302)
    response.set_cookie("flash_success", f"Order placed successfully! Total: ${total}", max_age=30)
    return response


@router.get("/marketplace/order-success", response_class=HTMLResponse)
async def order_success(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = auth.get_current_user(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    success_msg = request.cookies.get("flash_success", "Order placed successfully!")
    latest_order = db.query(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == "paid"
    ).order_by(models.Order.created_at.desc()).first()

    response = templates.TemplateResponse("marketplace/order_success.html", {
        "request": request,
        "current_user": current_user,
        "is_premium": current_user.subscription_tier == "premium",
        "success": success_msg,
        "order": latest_order
    })
    response.delete_cookie("flash_success")
    return response
