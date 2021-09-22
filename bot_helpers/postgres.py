import asyncpg
import psycopg2
from psycopg2.extensions import parse_dsn
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
DB_CONN = os.getenv("DB_CONN")


class Postgres:
    def __init__(self, bot) -> None:
        self.pool = None
        self.sync_conn = psycopg2.connect(parse_dsn(DB_CONN))

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

    def sync_execute(
        self, query: str, params: tuple, is_query=False, one_row=False, one_col=False
    ):
        with self.conn.cursor() as curs:
            curs.execute(query, params)
            if is_query:
                if one_row:
                    data = curs.fetchone()
                elif one_col:
                    data = [result[0] for result in curs.fetchall()]
                else:
                    data = curs.fetchall()
                return data
