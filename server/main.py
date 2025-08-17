import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List
import redis
from fastapi import FastAPI, Body, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from .api import healthcheck
from .api.v1.crud import download_quiz, generate_quiz, get_user_quiz_history
from .app.db.routes import router as db_router
from .app.db.routes.save_quiz_history import router as save_quiz_router
from .app.db.routes.get_quiz_history import router as get_quiz_history_router
from .app.db.routes.get_categories import router as get_categories_router
from .app.db.core.connection import startUp
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startUp()
    yield
load_dotenv()

origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

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

mock_db: List[UserModel] = []

@app.get("/api")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Quiz App API!"}

@app.post("/register/", response_model=UserModel)
def create_user(user: UserModel):
    if any(existing_user.username == user.username for existing_user in mock_db):
        raise HTTPException(status_code=400, detail="Username already taken")
    if any(existing_user.email == user.email for existing_user in mock_db):
        raise HTTPException(status_code=400, detail="Email already registered")
    mock_db.append(user)
    return user

@app.get("/users/", response_model=List[UserModel])
def list_users():
    return mock_db

@app.post("/login/", response_model=LoginResponseModel)
def login(request: LoginRequestModel):
    user = next(
        (
            u for u in mock_db 
            if (u.username == request.username_or_email or u.email == request.username_or_email)
            and u.password == request.password
        ),
        None
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user": user}

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
    return download_quiz(query.format, query.question_type, query.num_question)

app.include_router(save_quiz_router, prefix="/api")
app.include_router(get_quiz_history_router, prefix="/api")
app.include_router(get_categories_router, prefix="/api")




@app.get("/ping-redis")
def ping_redis():
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return {"pong": r.ping()}

