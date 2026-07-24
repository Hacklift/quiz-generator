import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


router = APIRouter()


@router.get("/healthcheck")
async def healthcheck():
    """Liveness probe: process is up and serving requests."""
    return {"status": "healthy"}


@router.get("/readyz")
async def readiness(request: Request):
    """Readiness probe: verifies MongoDB and Redis are reachable."""
    checks: dict[str, str] = {}

    try:
        await asyncio.wait_for(request.app.database.command("ping"), timeout=5)
        checks["mongodb"] = "ok"
    except Exception as exc:
        checks["mongodb"] = f"error: {type(exc).__name__}"

    try:
        await asyncio.wait_for(request.app.state.redis.ping(), timeout=5)
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"

    ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "unavailable", "checks": checks},
    )
