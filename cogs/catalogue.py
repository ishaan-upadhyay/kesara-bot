import asyncio
import asyncpg
import aiohttp
import os
import tekore as tk
from discord.ext import commands

CLIENT_ID = os.getenv('SPOT_ID')
CLIENT_SECRET = os.getenv('SPOT_SECRET')

class Catalogue(commands.Cog, name='catalogue'):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.group(case_insensitive=True)
    async def catalogue(self, ctx):
        pass

    @catalogue.command('view')    
    async def view(self, ctx):
        pass

    @catalogue.command('check')
    async def check(self, ctx, index: int):
        pass

    @catalogue.command('save')
    async def save(self, ctx, link: str):
        pass

    @catalogue.command('remove')
    async def remove(self, ctx, index: int):
        pass

async def get_info_spotify():
    pass