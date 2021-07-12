import os
import pylast

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(verbose=True)

LASTFM_KEY=os.getenv('LAST_KEY')
LASTFM_SECRET = os.getenv('LASTFM_SECRET')
class LastFM(commands.Cog, name="lastfm"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.network = pylast.LastFMNetwork(LASTFM_KEY, LASTFM_SECRET)
    
    @commands.group('fm')
    async def fm(self, ctx):
        ctx.other_target = bool(ctx.message.mentions)
        await get_username(ctx)

        if ctx.invoked_subcommand() is None:
            pass

    @fm.command('set')
    async def set(self, ctx, name: str):
        if ctx.other_target:
            #Should warn user that they are trying to set user for someone else
            pass
        
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
    async def unset(self, ctx):
        if ctx.other_target:
            pass

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

async def get_username(ctx):
    if ctx.other_target:
        ctx.target = ctx.message.raw_mentions[0]
    else:
        ctx.target = ctx.message.author.id

    ctx.lastfm_user = ctx.bot.db.execute(
        """SELECT lastfm FROM users WHERE user_id=$s""",
        ctx.target,
        is_query=True,
        one_val=True
    )