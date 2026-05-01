import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

async def main():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        print("url:", url)
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE t (
                  k TEXT, v INT NOT NULL,
                  PRIMARY KEY (k)
                )
            """))
            await conn.execute(
                text("INSERT INTO t (k, v) VALUES (:k, :v) "
                     "ON CONFLICT (k) DO UPDATE SET v = GREATEST(t.v, EXCLUDED.v)"),
                [{"k": "a", "v": 5}, {"k": "a", "v": 3}, {"k": "b", "v": 1}],
            )
            res = await conn.execute(text("SELECT k, v FROM t ORDER BY k"))
            print("rows:", res.fetchall())

            res = await conn.execute(text(
                "SELECT AVG(v::float) AS mean, "
                "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v::float) AS p50, "
                "COALESCE(STDDEV_POP(v::float), 0) AS sd FROM t"
            ))
            print("stats:", res.mappings().one())
        await engine.dispose()

asyncio.run(main())
