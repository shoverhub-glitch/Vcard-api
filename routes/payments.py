from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from datetime import datetime
from bson import ObjectId
from pathlib import Path
import aiofiles
import hashlib
import uuid

from database import get_database
from schemas.schemas import VerifyPaymentRequest

router = APIRouter(prefix="/api/payments", tags=["manual-payments"])

COLLECTION_NAME = "payments"
QR_CODES_DIR = Path("qrcodes")
QR_CODES_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_object_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(id)


def generate_verification_code() -> str:
    return str(uuid.uuid4())[:8].upper()


def hash_payment_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


@router.post("/generate-code/{template_id}")
async def generate_payment_code(template_id: str):
    validate_object_id(template_id)
    db = get_database()
    
    template = await db["templates"].find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not template.get("is_premium", False):
        raise HTTPException(status_code=400, detail="Template is not premium")
    
    code = generate_verification_code()
    hashed_code = hash_payment_code(code)
    
    payment_doc = {
        "template_id": template_id,
        "payment_code": hashed_code,
        "is_verified": False,
        "created_at": datetime.utcnow(),
    }
    
    await db[COLLECTION_NAME].insert_one(payment_doc)
    
    return {
        "template_id": template_id,
        "verification_code": code,
        "price": template.get("price"),
        "message": "Use this code to make payment"
    }


@router.post("/verify")
async def verify_payment(request_data: VerifyPaymentRequest):
    validate_object_id(request_data.template_id)
    db = get_database()
    
    hashed_code = hash_payment_code(request_data.payment_code)
    
    payment = await db[COLLECTION_NAME].find_one({
        "payment_code": hashed_code,
        "template_id": request_data.template_id,
    })
    
    if not payment:
        raise HTTPException(status_code=404, detail="Invalid payment code")
    
    if payment.get("is_verified", False):
        return {
            "success": True,
            "message": "Payment already verified",
            "access_token": f"{payment['_id']}_{request_data.payment_code}",
        }
    
    await db[COLLECTION_NAME].update_one(
        {"_id": payment["_id"]},
        {"$set": {"is_verified": True, "verified_at": datetime.utcnow()}}
    )
    
    return {
        "success": True,
        "message": "Payment verified successfully",
        "access_token": f"{payment['_id']}_{request_data.payment_code}",
    }


@router.post("/upload-qr/{template_id}")
async def upload_payment_qr(
    template_id: str,
    payment_code: str = Form(...),
    qr_image: UploadFile = File(...),
):
    validate_object_id(template_id)
    
    qr_image_content = await qr_image.read()
    if len(qr_image_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")
    
    filename = qr_image.filename or "qr.png"
    file_ext = filename.split('.')[-1].lower() if '.' in filename else 'png'
    qr_filename = f"{template_id}_{uuid.uuid4()}.{file_ext}"
    qr_path = QR_CODES_DIR / qr_filename
    
    async with aiofiles.open(qr_path, 'wb') as f:
        await f.write(qr_image_content)
    
    hashed_code = hash_payment_code(payment_code)
    
    db = get_database()
    payment_doc = {
        "template_id": template_id,
        "payment_code": hashed_code,
        "is_verified": False,
        "qr_image_path": str(qr_path),
        "created_at": datetime.utcnow(),
    }
    await db[COLLECTION_NAME].insert_one(payment_doc)
    
    return {
        "success": True,
        "message": "QR uploaded. Admin will verify within 24 hours.",
        "qr_path": f"/qrcodes/{qr_filename}",
    }


@router.get("/qr/{template_id}")
async def get_payment_qr(template_id: str):
    qr_files = list(QR_CODES_DIR.glob(f"{template_id}_*"))
    if not qr_files:
        raise HTTPException(status_code=404, detail="No QR codes found")
    latest_qr = max(qr_files, key=lambda p: p.stat().st_mtime)
    return FileResponse(latest_qr)
