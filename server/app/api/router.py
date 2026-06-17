import os

import redis
from fastapi import APIRouter, Request, Response

from server.app.api.health import router as health_router
from server.app.assistant.routes import router as assistant_router
from server.app.auth.routes import router as auth_router
from server.app.core.rate_limiter import limiter
from server.app.notifications.routes import router as notifications_router
from server.app.quiz.routes.categories import router as categories_router
from server.app.quiz.routes.canonical_quizzes import router as canonical_quizzes_router
from server.app.quiz.routes.downloads import router as downloads_router
from server.app.quiz.routes.folders import router as folders_router
from server.app.quiz.routes.generation import router as quiz_generation_router
from server.app.quiz.routes.grading import router as grading_router
from server.app.quiz.routes.history import router as history_router
from server.app.quiz.routes.live_sessions import router as live_quiz_router
from server.app.quiz.routes.provider_tokens import router as token_router
from server.app.quiz.routes.saved_quizzes import router as saved_quizzes_router
from server.app.share.routes import router as share_router
from server.app.users.routes import router as users_router


router = APIRouter()


@router.get("/api")
@limiter.limit("100/minute")
async def read_root(request: Request, response: Response):
    return {"message": "Welcome to the Quiz App API!"}


@router.get("/ping-redis")
@limiter.limit("10/minute")
async def ping_redis(request: Request, response: Response):
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return {"pong": redis_client.ping()}


router.include_router(health_router, prefix="/api", tags=["healthcheck"])
router.include_router(assistant_router, prefix="/api", tags=["assistant"])
router.include_router(auth_router, prefix="/auth", tags=["authentication"])
router.include_router(users_router)
router.include_router(quiz_generation_router, prefix="/api", tags=["quiz"])
router.include_router(canonical_quizzes_router, prefix="/api", tags=["quiz"])
router.include_router(grading_router, prefix="/api", tags=["quiz"])
router.include_router(downloads_router)
router.include_router(token_router, prefix="/api", tags=["Token"])
router.include_router(saved_quizzes_router, prefix="/api")
router.include_router(folders_router, prefix="/api/folders")
router.include_router(history_router, prefix="/api")
router.include_router(categories_router, prefix="/api")
router.include_router(live_quiz_router, prefix="/api/v1", tags=["Live Quiz"])
router.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])
router.include_router(share_router, prefix="/share", tags=["share"])
