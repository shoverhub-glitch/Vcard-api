from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
import uuid
import logging
import time

from database import connect_to_mongo, close_mongo_connection, get_database
from config import get_settings
from routes.templates import router as templates_router
from routes.payments import router as payments_router
from routes.razorpay import router as razorpay_router
from routes.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vcard")

settings = get_settings()

def parse_origins(origins_str: str) -> list:
    if not origins_str or origins_str == "*":
        return ["*"]
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

ALLOWED_ORIGINS = parse_origins(settings.allowed_origins)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await ensure_indexes()
    yield
    await close_mongo_connection()


async def ensure_indexes():
    db = get_database()
    
    await db.templates.create_index("event_type")
    await db.templates.create_index("is_premium")
    await db.templates.create_index("content_hash")
    await db.templates.create_index([("name", "text"), ("description", "text")])
    
    await db.payments.create_index("template_id")
    await db.payments.create_index("payment_code")
    await db.payments.create_index([("template_id", 1), ("is_verified", 1)])
    
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")
    
    logger.info("Database indexes ensured")


app = FastAPI(
    title="VCard API",
    description="Wedding Card Template Management API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    logger.info(f"[{request_id}] {request.method} {request.url.path} - Started")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"[{request_id}] {request.method} {request.url.path} - Error: {str(e)} - {process_time:.3f}s")
        raise


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


thumbnails_dir = Path("thumbnails")
thumbnails_dir.mkdir(exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory="thumbnails"), name="thumbnails")

templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

qrcodes_dir = Path("qrcodes")
qrcodes_dir.mkdir(exist_ok=True)
app.mount("/qrcodes", StaticFiles(directory="qrcodes"), name="qrcodes")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(razorpay_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "VCard API is running"}


@app.get("/health")
async def health_check():
    try:
        db = get_database()
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "request_id": request_id
        }
    )
