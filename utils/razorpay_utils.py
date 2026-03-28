import razorpay
from typing import Optional, Dict, Any
from config import get_settings

settings = get_settings()

_client: Optional[razorpay.Client] = None


def get_razorpay_client() -> razorpay.Client:
    global _client
    if _client is None:
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise ValueError("Razorpay credentials not configured")
        _client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
    return _client


def create_order(
    amount: int,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    client = get_razorpay_client()
    
    data = {
        "amount": amount * 100,
        "currency": currency,
        "receipt": receipt,
        "notes": notes or {},
    }
    
    try:
        order = client.order.create(data=data)
        return dict(order)
    except Exception as e:
        raise Exception(f"Failed to create order: {str(e)}")


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    import hmac
    import hashlib
    
    try:
        payload = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_signature = hmac.new(
            settings.razorpay_key_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, razorpay_signature)
    except Exception:
        return False


def get_payment(razorpay_payment_id: str) -> Dict[str, Any]:
    client = get_razorpay_client()
    
    try:
        payment = client.payment.fetch(razorpay_payment_id)
        return dict(payment)
    except Exception as e:
        raise Exception(f"Failed to fetch payment: {str(e)}")


def verify_webhook_signature(payload: str, signature: str) -> bool:
    import hmac
    import hashlib
    
    if not settings.razorpay_webhook_secret:
        return False
    
    expected_signature = hmac.new(
        settings.razorpay_webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
