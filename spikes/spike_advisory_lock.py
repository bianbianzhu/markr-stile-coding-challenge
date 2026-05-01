import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

DDL = "CREATE TABLE IF NOT EXISTS test_results (k TEXT PRIMARY KEY)"
KEY = 0x4D41524B


async def boot(engine, label):
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": KEY})
        await conn.execute(text(DDL))
        print(f"{label} done")


async def main():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        engine = create_async_engine(pg.get_connection_url())
        await asyncio.gather(boot(engine, "A"), boot(engine, "B"))
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT to_regclass('test_results')"))
            print("table:", res.scalar())
        await engine.dispose()


asyncio.run(main())
