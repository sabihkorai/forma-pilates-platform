from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str
    plan: Optional[str] = "none"


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    health_notes: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    age: Optional[int] = None
    phone: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


class SubscriptionCreate(BaseModel):
    plan_type: str
    payment_method_id: Optional[str] = None


class VideoFilter(BaseModel):
    category: Optional[str] = None
    difficulty: Optional[str] = None
    search: Optional[str] = None
    duration_filter: Optional[str] = None
    page: Optional[int] = 1


class MealPlanCreate(BaseModel):
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    goal: Optional[str] = "maintenance"
    dietary_preference: Optional[str] = "none"
    restrictions: Optional[str] = ""
    calories: Optional[int] = 1800


class OrderCreate(BaseModel):
    shipping_address: str
    payment_method_id: Optional[str] = None


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    cart_item_id: int
    quantity: int


class WearableConnect(BaseModel):
    device_type: str
    device_name: str


class EquipmentRequest(BaseModel):
    shipping_address: str
