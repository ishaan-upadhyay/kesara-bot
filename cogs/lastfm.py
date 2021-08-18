import os
import aiohttp
from discord import Embed

from discord.ext import commands
from discord.utils import escape_markdown as esc_md
from dotenv import load_dotenv

load_dotenv(verbose=True)

LASTFM_KEY = os.getenv("LAST_KEY")


class LastFM(commands.Cog, name="lastfm"):
    def __init__(self, bot) -> None:
        self.bot = bot

    def is_target_self(ctx):
        return not bool(ctx.message.mentions)

    @commands.group("fm")
    async def fm(self, ctx):
        await self.get_username(ctx)

        if ctx.invoked_subcommand is None:
            pass

    @fm.command("set")
    @commands.check(is_target_self)
    async def set(self, ctx, name: str):

        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, last_fm)
                VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
                SET last_fm = excluded.last_fm;
            """,
            str(ctx.target),
            name,
        )

        await ctx.send("Username successfully saved")

    @fm.command("unset")
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
            None,
        )

        await ctx.send("Username successfully removed")

    @fm.command(aliases=["np"])
    async def nowplaying(self, ctx):
        params = {
            "method": "user.getRecentTracks",
            "limit": "1",
            "user": f"{ctx.lastfm_user}",
        }

        info = await self.request_lastfm(params)

        title = (
            f"{esc_md(ctx.target.display_name)}'s Currently Playing"
            if info["recenttracks"]["track"][0]["@attr"]["nowplaying"] == "true"
            else f"{esc_md(ctx.target.display_name)}'s Recently Played"
        )

        description = f"{esc_md(info['recenttracks']['track'][0]['artist']['#text'])} - {esc_md(info['recenttracks']['track'][0]['name'])}"

        to_send = (
            Embed(title=title, description=description, colour=ctx.author.colour)
            .set_footer(
                text=f"Album: {info['recenttracks']['track'][0]['album']['#text']}"
            )
            .set_thumbnail(url=info["recenttracks"]["track"][0]["image"][1]["#text"])
        )

        await ctx.send(embed=to_send)

    # @fm.command()
    # async def

    async def get_playcount(self, artist, name, music_type, username=None):
        params = {"method": f"{music_type}.getInfo", "artist": artist}

        if name is not None:
            params[f"{music_type}"] = name
        if username is not None:
            params["username"] = username

        info = await self.request_lastfm(params)

        return (
            info[f"{music_type}"]["userplaycount"]
            if username is not None
            else info[f"{music_type}"]["playcount"]
        )

    async def request_lastfm(self, params):
        params |= {"api_key": LASTFM_KEY, "format": "json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://ws.audioscrobbler.com/2.0/", params=params
            ) as resp:

                info = await resp.json()
                print(info)

                if info is not None:
                    if resp.status == 200 and "error" not in info.keys():
                        return info
                    elif "error" in info.keys:
                        pass
                else:
                    pass

    async def get_username(self, ctx):
        if bool(ctx.message.mentions):
            ctx.target = ctx.message.mentions[0]
        else:
            ctx.target = ctx.author

        print(ctx.target)

        ctx.lastfm_user = await ctx.bot.db.execute(
            """SELECT last_fm FROM users WHERE user_id=$1""",
            str(ctx.target.id),
            is_query=True,
            one_val=True,
        )


def setup(bot):
    bot.add_cog(LastFM(bot))
