from fastapi import APIRouter

from ....app.db.routes.health import router as health_router

from ....app.db.routes.quizzes import router as quizzes_router

from ....app.db.routes.users import router as users_router

from ....app.db.routes.get_categories import router as get_categories_router


router = APIRouter()


router.include_router(health_router, prefix="/health", tags=["health"])

router.include_router(quizzes_router, prefix="/quizzes", tags=["quizzes"])

router.include_router(users_router, prefix="/users", tags=["users"])

router.include_router(get_categories_router, prefix="/api", tags=["categories"])

