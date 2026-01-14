from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import engine, Base
from app import models  # ensure models are registered with SQLAlchemy
from app.routers import chats, metrics, auth, google_auth, secretary
from app.routers import memories
from app.routers import audio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.invite import InviteCode
from app.utils.invite_manager import generate_code
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

settings = get_settings()

app = FastAPI(
    title="Secure LLM Chat API",
    description="API for interacting with LLMs with PII masking",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"https://.*\.ngrok-free\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"=== INCOMING REQUEST ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Origin: {request.headers.get('origin', 'No Origin')}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {str(e)}"})

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check for invite codes
    async with SessionLocal() as db:
        try:
            # Check if any invites exist
            result = await db.execute(select(InviteCode))
            invites = result.scalars().all()
            
            # Check if all used or empty
            all_used = all(invite.is_used for invite in invites)
            
            if not invites or all_used:
                logger.info("No active invite codes found. Generating 5 new codes...")
                new_codes = []
                for _ in range(5):
                    code = generate_code()
                    invite = InviteCode(code=code)
                    db.add(invite)
                    new_codes.append(code)
                
                await db.commit()
                logger.info(f"Generated 5 new invite codes: {', '.join(new_codes)}")
        except Exception as e:
            logger.error(f"Error checking/generating invite codes: {e}")

app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(secretary.router)
app.include_router(chats.router)
app.include_router(metrics.router)
app.include_router(memories.router)
app.include_router(audio.router)

from app.routers import digest
app.include_router(digest.router)

from app.routers import notifications
app.include_router(notifications.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Secure LLM Chat API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
