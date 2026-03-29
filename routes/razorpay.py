from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from bson import ObjectId
import hashlib

from database import get_database
from config import get_settings
from utils.razorpay_utils import create_order, verify_payment_signature, verify_webhook_signature

router = APIRouter(prefix="/payments", tags=["payments"])

settings = get_settings()


def validate_object_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(id)


class CreateOrderRequest(BaseModel):
    template_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    template_id: str


@router.get("/config")
async def get_razorpay_config():
    return {
        "key_id": settings.razorpay_key_id or "",
        "is_configured": bool(settings.razorpay_key_id and settings.razorpay_key_secret)
    }


@router.post("/create-order")
async def create_payment_order(request_data: CreateOrderRequest):
    validate_object_id(request_data.template_id)
    db = get_database()
    
    template = await db["templates"].find_one({"_id": ObjectId(request_data.template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not template.get("is_premium", False):
        raise HTTPException(status_code=400, detail="Template is not premium")
    
    price = template.get("price", 0)
    if price <= 0:
        raise HTTPException(status_code=400, detail="Invalid template price")
    
    try:
        payment_id = f"wcard_{hashlib.sha256(str(ObjectId()).encode()).hexdigest()[:12]}"
        
        order = create_order(
            amount=int(price),
            currency="INR",
            receipt=payment_id,
            notes={"template_id": request_data.template_id}
        )
        
        return {
            "success": True,
            "order_id": order["id"],
            "amount": price,
            "currency": "INR",
            "key_id": settings.razorpay_key_id,
            "payment_id": payment_id,
            "template_id": request_data.template_id,
            "template_name": template["name"],
            "description": f"Premium template: {template['name']}"
        }
    except ValueError:
        raise HTTPException(status_code=500, detail="Payment service unavailable")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create order")


@router.post("/verify-payment")
async def verify_payment(request_data: VerifyPaymentRequest):
    validate_object_id(request_data.template_id)
    
    is_valid = verify_payment_signature(
        razorpay_order_id=request_data.razorpay_order_id,
        razorpay_payment_id=request_data.razorpay_payment_id,
        razorpay_signature=request_data.razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    
    payment_code = f"{request_data.razorpay_payment_id[:8].upper()}"
    access_token = f"{payment_code}"
    
    return {
        "success": True,
        "message": "Payment verified successfully",
        "access_token": access_token,
        "payment_code": payment_code
    }


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    try:
        body = await request.body()
        signature = request.headers.get("x-razorpay-signature", "")
        
        if not verify_webhook_signature(body.decode(), signature):
            return {"status": "error", "message": "Invalid signature"}
        
        return {"status": "ok"}
    except Exception:
        return {"status": "error", "message": "Webhook processing failed"}


@router.get("/check/{template_id}")
async def check_payment_status(template_id: str, payment_code: str = ""):
    validate_object_id(template_id)
    return {"is_verified": bool(payment_code)}


@router.get("/resume/{template_id}")
async def resume_payment(template_id: str):
    validate_object_id(template_id)
    return {
        "success": True,
        "is_paid": False,
        "message": "No payment found"
    }


@router.get("/check-verification/{template_id}")
async def check_verification(template_id: str):
    validate_object_id(template_id)
    return {
        "is_verified": False,
        "message": "No verification found"
    }


@router.get("/order-by-payment-id/{payment_id}")
async def get_order_by_payment_id(payment_id: str):
    return {
        "success": True,
        "status": "unknown",
        "is_paid": False
    }
