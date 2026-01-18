"""FastAPI application main file."""

import os
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv

from api.routes import datasets, system, analytics, insights, auth
from utils.exceptions import LucidError
from utils.logging import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/lucid.log")
)

# Create FastAPI app
app = FastAPI(
    title="Lucid Backend API",
    description="Local-first analytics backend for Lucid desktop application",
    version="0.1.0"
)

# ✅ CORS middleware (Vite + Browser-safe + Tauri desktop app + Render)
# Register FIRST so it runs LAST (closest to routes)
# Get allowed origins from environment or use defaults
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # Additional common dev port
        "tauri://localhost",  # Tauri desktop app origin
        "http://tauri.localhost",  # Alternative Tauri origin
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https?://.*\.onrender\.com|https?://.*",  # Allow Render domains and any http/https origin
    allow_credentials=True,  # Allow credentials for auth
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=3600,  # Cache preflight for 1 hour
)

# Middleware to handle OPTIONS requests - Register LAST so it runs FIRST
@app.middleware("http")
async def options_handler_middleware(request: Request, call_next):
    """Handle OPTIONS preflight requests before they reach route handlers."""
    # ALWAYS handle OPTIONS requests here, never let them reach route handlers
    if request.method == "OPTIONS":
        origin = request.headers.get("origin", "")
        # Get allowed origins from environment or use defaults
        allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
        if allowed_origins_env:
            allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
        else:
            allowed_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "tauri://localhost",
                "http://tauri.localhost",
            ]
        
        # Also allow Render domains
        render_pattern = re.compile(r"https?://.*\.onrender\.com")
        
        headers = {
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
            "Access-Control-Max-Age": "3600",
        }
        
        # Handle null origin (Tauri apps send this) or missing origin
        if not origin or origin == "null" or origin == "undefined":
            # For Tauri desktop apps, allow any origin
            headers["Access-Control-Allow-Origin"] = "*"
            # Also allow credentials if needed (though * with credentials won't work in browsers)
            # This is fine for Tauri apps which don't follow same-origin policy strictly
        elif origin in allowed_origins or render_pattern.match(origin):
            headers["Access-Control-Allow-Origin"] = origin
        else:
            # Allow any origin for OPTIONS preflight (browser will validate actual request)
            # This is safe for OPTIONS requests
            headers["Access-Control-Allow-Origin"] = "*"
        
        return Response(status_code=200, headers=headers)
    
    # For non-OPTIONS requests, let CORS middleware handle headers
    response = await call_next(request)
    return response

# Register routes
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(analytics.router)
app.include_router(insights.router)

# Global exception handler
@app.exception_handler(LucidError)
async def lucid_exception_handler(request, exc: LucidError):
    logger.error(f"Lucid error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": exc.__class__.__name__,
                "message": str(exc),
                "details": None
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": None
            }
        }
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Lucid Backend API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Lucid Backend API shutting down...")
