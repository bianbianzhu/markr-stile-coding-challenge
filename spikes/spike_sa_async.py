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
            await conn.execute(
                text("""
                CREATE TABLE t (
                  k TEXT, v INT NOT NULL,
                  PRIMARY KEY (k)
                )
            """)
            )
            await conn.execute(
                text("""
                INSERT INTO t (k, v)
                VALUES (:k1, :v1), (:k2, :v2), (:k3, :v3)
            """),
                {"k1": "a", "v1": 2, "k2": "b", "v2": 7, "k3": "c", "v3": 4},
            )
            res = await conn.execute(text("SELECT k, v FROM t ORDER BY k"))
            print("initial rows:", res.fetchall())

            # Ingestion dedups first, so no VALUES list contains duplicate conflict keys.
            await conn.execute(
                text("""
                INSERT INTO t (k, v)
                VALUES (:k1, :v1), (:k2, :v2), (:k3, :v3)
                ON CONFLICT (k) DO UPDATE SET v = GREATEST(t.v, EXCLUDED.v)
            """),
                {"k1": "a", "v1": 5, "k2": "b", "v2": 1, "k3": "c", "v3": 3},
            )
            res = await conn.execute(text("SELECT k, v FROM t ORDER BY k"))
            print("rows:", res.fetchall())

            res = await conn.execute(
                text(
                    "SELECT AVG(v::float) AS mean, "
                    "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v::float) AS p50, "
                    "COALESCE(STDDEV_POP(v::float), 0) AS sd FROM t"
                )
            )
            print("stats:", res.mappings().one())
        await engine.dispose()


asyncio.run(main())
