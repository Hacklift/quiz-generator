import asyncio

from .databaseSeeding import restoreSeed_database



if __name__ == "__main__":

    asyncio.run(restoreSeed_database())


