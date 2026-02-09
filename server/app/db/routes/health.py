from fastapi import APIRouter

from ..schemas.database_schema import SeedDatabaseResponse

from ...databaseSeeding import seed_database, restoreSeed_database

from ....app.db.core.connection import database




router = APIRouter()


@router.get("/dbhealth")

async def health_check():

    try:

        await database.command("ping")

        return {"status": "healthy"}

    except Exception as e:

        return {"status": "unhealthy", "error": str(e)}



@router.post("/seed-database", response_model=SeedDatabaseResponse)

async def trigger_seeding():

    try:

        await seed_database()

        return SeedDatabaseResponse(message=f"Database seeding process completed successfully!")

    except Exception as e:

        return {"error seeding database": str(e)}



@router.post("/restore-database", response_model=SeedDatabaseResponse)

async def trigger_seeding():

    try:

        await restoreSeed_database()

        return SeedDatabaseResponse(message=f"Database default restore process completed successfully!")

    except Exception as e:

        return {"error seeding database": str(e)}

