from testcontainers.postgres import PostgresContainer
with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
    print("url:", pg.get_connection_url())
    print("host:", pg.get_container_host_ip())
    print("port:", pg.get_exposed_port(5432))
