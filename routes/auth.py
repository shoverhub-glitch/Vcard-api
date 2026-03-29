from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional

from database import get_database
from schemas.schemas_auth import LoginRequest, LoginResponse, UserResponse, UserInDB
from utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer()

USERS_COLLECTION = "users"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    token = credentials.credentials
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db = get_database()
    user = await db[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
    
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="User account is disabled",
        )
    
    return UserInDB(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        hashed_password=user["hashed_password"],
        is_active=user.get("is_active", True),
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


async def get_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user


@router.post("/login", response_model=LoginResponse)
async def login(request_data: LoginRequest):
    db = get_database()
    
    user = await db[USERS_COLLECTION].find_one({
        "email": request_data.email,
        "is_active": True
    })
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )
    
    if not verify_password(request_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )
    
    await db[USERS_COLLECTION].update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user["role"]}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            role=user["role"],
            is_active=user.get("is_active", True),
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.post("/logout")
async def logout(current_user: UserInDB = Depends(get_current_user)):
    return {"message": "Successfully logged out"}


@router.get("/verify")
async def verify_token(current_user: UserInDB = Depends(get_current_user)):
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
        }
    }
