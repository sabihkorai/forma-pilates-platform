from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)
    health_notes = Column(Text, nullable=True)
    subscription_tier = Column(String(50), default="none")
    stripe_customer_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Body measurements
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    phone = Column(String(50), nullable=True)

    subscriptions = relationship("Subscription", back_populates="user")
    workout_sessions = relationship("WorkoutSession", back_populates="user")
    meal_plans = relationship("MealPlan", back_populates="user")
    wearable_devices = relationship("WearableDevice", back_populates="user")
    equipment_loans = relationship("EquipmentLoan", back_populates="user")
    orders = relationship("Order", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_type = Column(String(50), nullable=False)
    monthly_price = Column(Float, nullable=False)
    stripe_subscription_id = Column(String(255), nullable=True)
    status = Column(String(50), default="active")
    start_date = Column(DateTime, default=datetime.utcnow)
    renewal_date = Column(DateTime, nullable=True)
    cancelled_date = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="subscriptions")
    equipment_loans = relationship("EquipmentLoan", back_populates="subscription")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=False)
    difficulty_level = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    instructor_name = Column(String(255), nullable=False)
    thumbnail_url = Column(String(512), nullable=True)
    video_url = Column(String(512), nullable=False)
    tags = Column(Text, nullable=True)
    view_count = Column(Integer, default=0)
    rating = Column(Float, default=4.5)
    is_premium = Column(Boolean, default=False)
    published_at = Column(DateTime, default=datetime.utcnow)

    workout_sessions = relationship("WorkoutSession", back_populates="video")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    duration_completed_seconds = Column(Integer, default=0)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="workout_sessions")
    video = relationship("Video", back_populates="workout_sessions")


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    meals_data = Column(Text, nullable=True)
    macros = Column(Text, nullable=True)
    shopping_list = Column(Text, nullable=True)
    dietary_preferences = Column(String(255), nullable=True)
    health_goals = Column(String(255), nullable=True)
    restrictions = Column(Text, nullable=True)
    is_saved = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="meal_plans")


class WearableDevice(Base):
    __tablename__ = "wearable_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_type = Column(String(50), nullable=False)
    device_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="wearable_devices")


class EquipmentLoan(Base):
    __tablename__ = "equipment_loans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    equipment_list = Column(Text, nullable=True)
    loan_value = Column(Float, default=200.0)
    status = Column(String(50), default="pending")
    shipping_address = Column(Text, nullable=True)
    shipped_date = Column(DateTime, nullable=True)
    delivered_date = Column(DateTime, nullable=True)
    ownership_transfer_date = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="equipment_loans")
    subscription = relationship("Subscription", back_populates="equipment_loans")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=100)
    category = Column(String(100), nullable=True)
    image_url = Column(String(512), nullable=True)
    tags = Column(Text, nullable=True)
    sales_count = Column(Integer, default=0)

    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_order_id = Column(String(255), nullable=True)
    status = Column(String(50), default="pending")
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    shipping_address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
