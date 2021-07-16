import os
import aiohttp

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(verbose=True)

LASTFM_KEY=os.getenv('LAST_KEY')
class LastFM(commands.Cog, name="lastfm"):
    def __init__(self, bot) -> None:
        self.bot = bot

    def is_target_self(self, ctx):
        return not bool(ctx.message.mentions)
    
    @commands.group('fm')
    async def fm(self, ctx):
        await get_username(ctx)
        
        if ctx.invoked_subcommand() is None:
            pass

    @fm.command('set')
    @commands.check(is_target_self)
    async def set(self, ctx, name: str):
        
        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, last_fm)
                VALUES ($s $s)
            ON CONFLICT (user_id) DO UPDATE
                SET last_fm = excluded.last_fm;
            """,
            ctx.target,
            name
        )
    
    @fm.command('unset')
    @commands.check(is_target_self)
    async def unset(self, ctx):

        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, last_fm)
                VALUES ($s $s)
            ON CONFLICT (user_id) DO UPDATE
                SET last_fm = excluded.last_fm;
            """,
            ctx.target,
            None        
        )

    @fm.command(aliases=['np'])
    async def nowplaying(self, ctx):
        pass

    # @fm.command()
    # async def 

async def request_lastfm(self, params):
    params |= {'api_key': LASTFM_KEY, 'format': 'json'}
    async with aiohttp.ClientSession() as session:
        async with session.get('http://ws.audioscrobbler.com/2.0/', params) as resp:
            info = resp.json()
            if resp.status == 200:
                return info

async def get_username(ctx):
    if bool(ctx.message.mentions):
        ctx.target = ctx.message.raw_mentions[0]
    else:
        ctx.target = ctx.message.author.id

    ctx.lastfm_user = ctx.bot.db.execute(
        """SELECT lastfm FROM users WHERE user_id=$s""",
        ctx.target,
        is_query=True,
        one_val=True
    )