from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    WEDDING = "wedding"
    BIRTHDAY = "birthday"
    BABY_SHOWER = "baby_shower"
    ANNIVERSARY = "anniversary"
    ENGAGEMENT = "engagement"
    GRADUATION = "graduation"
    CORPORATE = "corporate"
    MEHNDI = "mehndi"
    RECEPTION = "reception"
    HALDI = "haldi"
    OTHER = "other"


class TemplateBase(BaseModel):
    name: str
    description: str = ""
    thumbnail: Optional[str] = ""
    category: str = "modern"
    tags: List[str] = []
    event_type: EventType = EventType.WEDDING
    is_premium: bool = False
    price: Optional[float] = None
    supports_image: bool = True


class TemplateCreate(TemplateBase):
    html_content: str


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    html_content: Optional[str] = None
    event_type: Optional[EventType] = None
    is_premium: Optional[bool] = None
    price: Optional[float] = None
    supports_image: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: str
    content_hash: Optional[str] = ""
    has_html: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentVerificationCreate(BaseModel):
    template_id: str
    payment_code: str
    payment_screenshot: Optional[str] = None


class PaymentVerificationResponse(BaseModel):
    id: str
    template_id: str
    payment_code: str
    is_verified: bool
    verified_at: Optional[datetime] = None
    created_at: datetime


class VerifyPaymentRequest(BaseModel):
    payment_code: str
    template_id: str
