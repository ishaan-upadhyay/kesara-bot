import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
DB_CONN = os.getenv("DB_CONN")


class Postgres:
    def __init__(self, bot) -> None:
        self.pool = None

    async def init_pool(self) -> None:
        self.pool = await asyncpg.create_pool(dsn=DB_CONN)
        print("Pool initialized")

    async def close_pool(self):
        await self.pool.close()

    async def execute(
        self,
        statement,
        *params,
        is_query=False,
        one_val=False,
        one_row=False,
        one_col=False
    ):
        async with self.pool.acquire() as con:
            async with con.transaction():
                if is_query:
                    if one_val:
                        data = await con.fetchval(statement, *params)
                    elif one_row:
                        data = await con.fetchrow(statement, *params)
                    elif one_col:
                        data = [
                            result[0] async for result in con.cursor(statement, *params)
                        ]
                    else:
                        data = await con.fetch(statement, *params)
                    return data if data is not None else ()
                else:
                    await con.execute(statement, *params)
                    return ()

    async def executemany(self, statement, *params):
        async with self.pool.acquire() as con:
            async with con.transaction():
                con.executemany(statement, params)
            return ()

    async def iterate(self, statement, *params):
        async with self.pool.acquire() as con:
            async with con.transaction():
                async with con.cursor() as curs:
                    pass
