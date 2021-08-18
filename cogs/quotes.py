import random
import asyncio
from bot_helpers import pagination  # pylint: disable=import-error
from discord import Member, Embed
from discord.ext import commands
from discord.utils import escape_markdown as esc_md


class Quotes(commands.Cog, name="quotes"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(case_insensitive=True)
    async def quotes(self, ctx):
        pass

    @quotes.command(description="Enable quotes functionality for a user.")
    @commands.has_permissions(manage_messages=True)
    async def adduser(self, ctx: commands.Context, member: Member = None):

        target = member if member is not None else ctx.author

        await self.bot.db.execute(
            """INSERT INTO quotes 
               VALUES ($1, $2, $3)
               ON CONFLICT DO NOTHING
            """,
            str(ctx.guild.id),
            str(target.id),
            [],
        )

        to_send = (
            Embed(
                title="Added user",
                description=f"{esc_md(target.display_name)} added to quotes - \n Start adding quotes using {ctx.prefix}quotes add",
                colour=target.colour,
            )
            .set_footer(
                text=f"Added by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
            .set_thumbnail(url=target.avatar_url)
        )

        await ctx.send(embed=to_send)

    @quotes.command(description="Disables quotes functionality for a user.")
    @commands.has_permissions(manage_messages=True)
    async def removeuser(self, ctx: commands.Context, member: Member = None):
        def check(reaction, user) -> bool:
            return (
                user == ctx.author
                and str(reaction.emoji) == "✅"
                and reaction.message.id == confirm_msg.id
            )

        target = member if member is not None else ctx.author
        confirm_msg = await ctx.send(
            f"Are you sure you'd like to remove {target.mention}'s quotes? React with ✅ to confirm."
        )

        try:
            reaction, user = await self.bot.wait_for(
                event="reaction_add", check=check, timeout=90.0
            )
        except asyncio.TimeoutError:
            await ctx.send("No confirmation received.")
        else:

            count = await self.bot.db.execute(
                """DELETE FROM quotes
                WHERE guild_id = $1
                AND user_id = $2
                RETURNING cardinality(quotes)
                """,
                str(ctx.guild.id),
                str(target.id),
                is_query=True,
                one_val=True,
            )

            to_send = (
                Embed(
                    title="Removed user",
                    description=f"{esc_md(target.display_name)} removed from quotes - \n had {count} quotes on this server",
                    colour=ctx.author.colour,
                )
                .set_footer(
                    text=f"Removed by {ctx.author.display_name}",
                    icon_url=ctx.author.avatar_url,
                )
                .set_thumbnail(url=member.avatar_url)
            )

            await ctx.send(embed=to_send)

    @quotes.command(description="Add a quote for user.")
    async def add(self, ctx, quote: str, member: Member = None):

        target = member if member is not None else ctx.author

        await self.bot.db.execute(
            """UPDATE quotes
           SET quotes = quotes || $1
           WHERE guild_id = $2
           AND user_id = $3
        """,
            [esc_md(quote)],
            str(ctx.guild.id),
            str(target.id),
        )

        to_send = (
            Embed(title="Added quote", description=esc_md(quote), colour=target.colour)
            .set_author(name=target.display_name, url=target.avatar_url)
            .set_footer(
                text=f"Added by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )

        await ctx.send(embed=to_send)

    @quotes.command(description="Remove a quote for a user.")
    async def remove(self, ctx: commands.Context, index: int, member: Member = None):
        target = member if member is not None else ctx.author

        removed = await self.bot.db.execute(
            """UPDATE quotes
           SET quotes = array_remove(quotes, quotes[$1])
           WHERE guild_id = $2
           and user_id = $3
           RETURNING quotes[$1]
        """,
            index,
            str(ctx.guild.id),
            str(target.id),
            is_query=True,
            one_val=True,
        )

        to_send = (
            Embed(title="Removed quote", description=removed, colour=target.colour)
            .set_author(name=esc_md(target.display_name), url=target.avatar_url)
            .set_footer(
                text=f"Removed by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )

        await ctx.send(embed=to_send)

    @quotes.command(description="Retrieve a quote at random for a specific user.")
    async def random(self, ctx: commands.Context, member: Member = None):
        target = member if member is not None else ctx.author

        quotes = await self.bot.db.execute(
            """SELECT quotes FROM quotes WHERE guild_id=$1 AND user_id=$2""",
            str(ctx.guild.id),
            str(target.id),
            is_query=True,
            one_val=True,
        )

        quote = random.choice(quotes)

        to_send = (
            Embed(
                title=f"Quote from {esc_md(target.display_name)}",
                description=quote,
                colour=target.colour,
            )
            .set_thumbnail(url=target.avatar_url)
            .set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )

        await ctx.send(embed=to_send)

    @quotes.command(description="View a specific quote for a user.")
    async def view(self, ctx, index: int, member: Member = None):
        target = member if member is not None else ctx.author

        quote = await self.bot.db.execute(
            """SELECT quotes[$1] FROM quotes WHERE guild_id=$2 AND user_id=$3""",
            index,
            str(ctx.guild.id),
            str(target.id),
            is_query=True,
            one_val=True,
        )

        to_send = (
            Embed(
                title=f"Quote from {esc_md(target.display_name)}",
                description=quote,
                colour=target.colour,
            )
            .set_thumbnail(url=target.avatar_url)
            .set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )

        await ctx.send(embed=to_send)

    @quotes.command(description="View a list of quotes from a specific user.")
    async def userlist(self, ctx, member: Member = None):
        target = member if member is not None else ctx.author

        quotes = await self.bot.db.execute(
            """SELECT quotes FROM quotes WHERE guild_id=$1 AND user_id=$2""",
            str(ctx.guild.id),
            str(target.id),
            is_query=True,
            one_val=True,
        )

        for idx, quote in enumerate(quotes):
            quotes[idx] = (
                f'"*{quote}*"' if len(quote) < 196 else f'"*{quote[:193]}...*"'
            )

        to_send = (
            Embed(
                title=f"Quotes from {esc_md(target.display_name)}",
                description="",
                colour=target.colour,
            )
            .set_thumbnail(url=target.avatar_url)
            .set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )
        if quotes != []:
            await pagination.send_pages(ctx, to_send, quotes)
        else:
            await ctx.send("This user has no quotes added yet.")

    @quotes.command(
        description="View a list of users in this server with quotes enabled."
    )
    async def serverlist(self, ctx: commands.Context):
        users = await self.bot.db.execute(
            """SELECT user_id FROM quotes where guild_id=$1""",
            str(ctx.guild.id),
            is_query=True,
            one_col=True,
        )

        members = [None] * len(users)

        for idx, user in enumerate(users):
            members[idx] = await ctx.guild.fetch_member(user)

        usernames = [esc_md(member.display_name) for member in members]

        to_send = (
            Embed(
                title=f"Users with quotes from {esc_md(ctx.guild.name)}",
                description="",
                colour=ctx.author.colour,
            )
            .set_thumbnail(url=ctx.guild.icon_url)
            .set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )
        if usernames != []:
            await pagination.send_pages(ctx, to_send, usernames)
        else:
            await ctx.send("This server has no users added to the quotes database.")


def setup(bot):
    bot.add_cog(Quotes(bot))