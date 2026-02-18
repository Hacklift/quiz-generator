from fastapi.responses import StreamingResponse
from .api import healthcheck
import logging
import os
from redis.asyncio import Redis
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, Body, HTTPException, Depends, Query, Request, Response
import redis
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api import healthcheck
from .api.v1.crud import download_quiz, generate_quiz, get_user_quiz_history
from .app.db.routes import router as db_router
from .app.db.core.connection import startUp, database
from .app.db.core.connection import (
    startUp, 
    get_users_collection, 
    get_quizzes_collection, 
    get_blacklisted_tokens_collection
)
from server.app.quiz.routers.quiz import router as quiz_router
from server.app.auth.routes import router as auth_router
from server.app.db.routes.save_quiz_history import router as save_quiz_router
from server.app.db.routes.get_quiz_history import router as get_quiz_history_router
from .app.db.routes.get_categories import router as get_categories_router
from .app.db.routes.folder_routes import router as folder_routes
from .app.db.routes import saved_quizzes

from .app.db.core.connection import startUp
from .app.db.routes import token_router
from .app.quiz.routers.quiz import router as quiz_router
from .app.share.routes.share_routes import router as share_router
from .schemas.model import UserModel, LoginRequestModel, LoginResponseModel
from .schemas.query import (
    GenerateQuizQuery,
    DownloadQuizQuery,
    GetUserQuizHistoryQuery
)

# Import rate limiter
from .app.db.core.rate_limiter import limiter, rate_limit_handler
from .app.db.core.config import settings
from .app.dependancies import get_current_user
from .app.db.models.user_models import UserOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

load_dotenv()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startUp()
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    app.state.redis = redis_client
    app.state.users_collection = get_users_collection()
    app.state.quizzes_collection = get_quizzes_collection()
    app.state.blacklisted_tokens_collection = get_blacklisted_tokens_collection()
    
    yield
    
    get_users_collection().database.client.close()
    await redis_client.close()

app = FastAPI(lifespan=lifespan)

# CRITICAL: Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(db_router)
app.include_router(quiz_router, prefix="/api", tags=["quiz"])
app.include_router(share_router, prefix="/share", tags=["share"])
app.include_router(healthcheck.router, prefix="/api", tags=["healthcheck"])
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(token_router.router, prefix="/api", tags=["Token"])
app.include_router(saved_quizzes.router, prefix="/api", tags=["Saved Quizzes"])
app.include_router(folder_routes, prefix="/api/folders", tags=["Folders"])

app.include_router(save_quiz_router, prefix="/api")
app.include_router(get_quiz_history_router, prefix="/api")
app.include_router(get_categories_router, prefix="/api")

app.database = database

# Apply rate limits to main endpoints
@app.get("/api")
@limiter.limit("100/minute")
async def read_root(request: Request, response: Response):
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Quiz App API!"}

@app.get("/users")
@limiter.limit("30/minute")  # Restrictive for user listing
async def get_users(
    request: Request,
    response: Response,
    current_user: UserOut = Depends(get_current_user),
):
    if not settings.ENABLE_PUBLIC_USER_LIST and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users_collection = request.app.state.users_collection
    users = await users_collection.find(
        {},
        projection={
            "hashed_password": 0,
            "refresh_token": 0,
            "refresh_token_jti": 0,
            "refresh_token_expires_at": 0,
        },
    ).to_list(length=100)
    return users

@app.post("/generate-quiz")
@limiter.limit("10/minute;50/hour")  # Resource-intensive operation
async def generate_quiz_handler(
    request: Request,
    response: Response,
    query: GenerateQuizQuery = Body(...)
) -> Dict[str, Any]:
    logger.info("Received query: %s", query)
    return generate_quiz(query.user_id, query.question_type, query.num_question)

@app.post("/get-user-quiz-history")
@limiter.limit("50/minute")
async def get_user_quiz_history_handler(
    request: Request,
    response: Response,
    query: GetUserQuizHistoryQuery = Body(...)
) -> List[Any]:
    logger.info("Received query: %s", query)
    return get_user_quiz_history(query.user_id)

@app.get("/download-quiz")
@limiter.limit("20/minute")
async def download_quiz_handler(
    request: Request,
    response: Response,
    query: DownloadQuizQuery = Depends()
) -> StreamingResponse:
    logger.info("Received query: %s", query)
    return download_quiz(query.format, query.question_type, query.num_question)

@app.get("/ping-redis")
@limiter.limit("10/minute")
async def ping_redis(request: Request, response: Response):
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return {"pong": r.ping()}
