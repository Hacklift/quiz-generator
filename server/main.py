from fastapi.responses import StreamingResponse
from .api import healthcheck
import logging
import os
import jwt
from redis.asyncio import Redis
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, Body, HTTPException, Depends, Query, Request
import redis
from fastapi import FastAPI, Body, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from .api import healthcheck
from .api.v1.crud import generate_quiz, get_user_quiz_history
from .api.v1.crud.downloads.download_quiz import download_mock_quiz, download_quiz_by_id
from .app.db.routes import router as db_router
from .app.db.core.connection import startUp, database
from motor.motor_asyncio import AsyncIOMotorCollection
from .app.db.core.connection import startUp, get_users_collection, get_quizzes_collection, get_blacklisted_tokens_collection
from server.app.quiz.routers.quiz import router as quiz_router
from server.app.auth.routes import router as auth_router
from server.app.db.routes.save_quiz_history import router as save_quiz_router
from server.app.db.routes.get_quiz_history import router as get_quiz_history_router
from server.app.db.core.connection import startUp
from server.app.quiz.routers.quiz import router as quiz_router
from .app.db.routes.save_quiz_history import router as save_quiz_router
from .app.db.routes.get_quiz_history import router as get_quiz_history_router
from .app.db.routes.get_categories import router as get_categories_router
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
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
    redis = Redis.from_url(redis_url, decode_responses=True)
    app.state.redis = redis

    app.state.users_collection = get_users_collection()
    app.state.quizzes_collection = get_quizzes_collection()
    app.state.blacklisted_tokens_collection = get_blacklisted_tokens_collection()

    yield

    get_users_collection().database.client.close()
    await redis.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(db_router)
app.include_router(quiz_router, prefix="/api", tags=["quiz"])
app.include_router(share_router, prefix="/share", tags=["share"])
app.include_router(healthcheck.router, prefix="/api", tags=["healthcheck"])
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(token_router.router, prefix="/api", tags=["Token"])
app.database = database


@app.get("/api")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Quiz App API!"}


@app.get("/users")
async def get_users(request: Request):
    users_collection = request.app.state.users_collection
    users = await users_collection.find().to_list(length=100)
    return users

@app.post("/generate-quiz")
async def generate_quiz_handler(query: GenerateQuizQuery = Body(...)) -> Dict[str, Any]:
    logger.info("Received query: %s", query)
    return generate_quiz(query.user_id, query.question_type, query.num_question)

@app.post("/get-user-quiz-history")
def get_user_quiz_history_handler(query: GetUserQuizHistoryQuery = Body(...)) -> List[Any]:
    logger.info("Received query: %s", query)
    return get_user_quiz_history(query.user_id)


@app.get("/download-quiz")
async def download_quiz_handler(query: DownloadQuizQuery = Depends()) -> StreamingResponse:
    logger.info("Received query: %s", query)

    if query.quiz_id:
        return await download_quiz_by_id(
            quiz_id=query.quiz_id,
            file_format=query.format,
            user_id=query.user_id
        )

    return download_mock_quiz(
        query.format,
        query.question_type,
        query.num_question
    )


app.include_router(save_quiz_router, prefix="/api")
app.include_router(get_quiz_history_router, prefix="/api")
app.include_router(get_categories_router, prefix="/api")

@app.get("/ping-redis")
def ping_redis():
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return {"pong": r.ping()}

