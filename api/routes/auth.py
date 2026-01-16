"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import secrets
from datetime import datetime, timedelta

from storage.database import Database
from utils.exceptions import DatabaseError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# In-memory session store (for demo - use Redis in production)
sessions = {}

# Initialize database
import os
from dotenv import load_dotenv
load_dotenv()
db_path = os.getenv("DATABASE_PATH", "data/nafah.db")
db = Database(db_path)


class SignupRequest(BaseModel):
    name: str
    shop_name: Optional[str] = None
    company_name: Optional[str] = None
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LogoutRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None


def hash_password(password: str) -> str:
    """Hash password using SHA256 (use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    """Generate a random session token."""
    return secrets.token_urlsafe(32)


async def get_current_user(token: str) -> Optional[dict]:
    """Get current user from session token."""
    session = sessions.get(token)
    if not session:
        return None
    
    # Check if session expired (24 hours)
    if datetime.now() - session["created_at"] > timedelta(hours=24):
        del sessions[token]
        return None
    
    return session["user"]


# OPTIONS handlers removed - handled by middleware in main.py
# Keeping these commented out as backup if middleware doesn't work
# @router.options("/signup")
# @router.options("/login")
# @router.options("/logout")
# @router.options("/me")
# async def auth_options(request: Request):
#     """Handle OPTIONS preflight requests for auth routes."""
#     origin = request.headers.get("origin", "")
#     allowed_origins = [
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#         "http://localhost:3000",
#     ]
#     
#     headers = {
#         "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
#         "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
#         "Access-Control-Max-Age": "3600",
#     }
#     
#     if origin in allowed_origins:
#         headers["Access-Control-Allow-Origin"] = origin
#     else:
#         headers["Access-Control-Allow-Origin"] = "*"
#     
#     return Response(status_code=200, headers=headers)

@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Create a new user account."""
    try:
        # Check if user already exists
        existing = await db.execute_query(
            "SELECT id FROM users WHERE email = ?",
            (request.email,),
            fetch_one=True
        )
        
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        hashed_password = hash_password(request.password)
        
        # Use shop_name or company_name (prefer shop_name)
        store_name = request.shop_name or request.company_name or None
        
        # Create user
        user_id = await db.execute_write(
            """
            INSERT INTO users (name, email, password_hash, shop_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (request.name, request.email, hashed_password, store_name, datetime.now().isoformat()),
            return_id=True
        )
        
        # Get the created user
        created_user = await db.execute_query(
            "SELECT id, name, email, shop_name FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        
        # Generate session token
        token = generate_token()
        user = {
            "id": created_user["id"],
            "name": created_user["name"],
            "email": created_user["email"],
            "shop_name": created_user.get("shop_name"),
            "company_name": created_user.get("shop_name")  # For compatibility
        }
        
        sessions[token] = {
            "user": user,
            "created_at": datetime.now()
        }
        
        return AuthResponse(
            success=True,
            message="Account created successfully",
            token=token,
            user=user
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create account: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Authenticate user and create session."""
    try:
        # Find user
        user = await db.execute_query(
            "SELECT id, name, email, password_hash, shop_name, company_name FROM users WHERE email = ?",
            (request.email,),
            fetch_one=True
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        hashed_password = hash_password(request.password)
        if user["password_hash"] != hashed_password:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Generate session token
        token = generate_token()
        user_data = {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "shop_name": user.get("shop_name"),
            "company_name": user.get("company_name") or user.get("shop_name")  # For compatibility
        }
        
        sessions[token] = {
            "user": user_data,
            "created_at": datetime.now()
        }
        
        return AuthResponse(
            success=True,
            message="Login successful",
            token=token,
            user=user_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to login: {str(e)}")


@router.post("/logout")
async def logout(request: LogoutRequest):
    """Logout user and invalidate session."""
    if request.token in sessions:
        del sessions[request.token]
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_me(token: str):
    """Get current user information."""
    user = await get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"success": True, "user": user}
