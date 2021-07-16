import random
import asyncio
from bot_helpers import pagination # pylint: disable=import-error
from discord import Member, Embed
from discord.ext import commands
from discord.utils import escape_markdown as esc_md
from discord.ext.commands.core import has_permissions

class Quotes(commands.Cog, name='quotes'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def has_manage_messages_or_quotes_role(self, ctx):
        return 
    
    @commands.group(case_insensitive=True)
    async def quotes(self, ctx):
        pass

    @quotes.command()
    @has_permissions(manage_messages=True)
    async def adduser(self, ctx: commands.Context, member: Member):

        target = member if member is not None else ctx.author

        await self.bot.db.execute(
            """INSERT INTO quotes 
               VALUES ($1, $2, $3)
               ON CONFLICT DO NOTHING
            """,
            ctx.guild.id,
            target.id,
            []
        )

        to_send = Embed(title="Added user",
                        description=f"{esc_md(target.display_name)} added to quotes - \n Start adding quotes using {ctx.prefix}quotes add",
                        colour=target.colour
                       ).set_footer(
                        text=f"Added by {esc_md(ctx.author.display_name)}",
                        icon_url=ctx.author.avatar_url
                       ).set_thumbnail(
                           url=target.avatar_url
                       )
        
        ctx.send(embed=to_send)

    @quotes.command()
    async def removeuser(self, ctx: commands.Context, member: Member):
    
        def check(reaction, user) -> bool:
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id
        
        target = member if member is not None else ctx.author
        confirm_msg = await ctx.send(f"Are you sure you'd like to remove {target.mention}'s quotes? React with ✅ to confirm.")
        
        try:
            reaction, user = await self.bot.wait_for(event="reaction_add", check=check, timeout=90.0)
        except asyncio.TimeoutError:
            await ctx.send("No confirmation received.")
        else:

            count = await self.bot.db.execute(
                """DELETE FROM quotes
                WHERE guild_id = $1
                AND user_id = $2
                RETURNING cardinality(quotes_array)
                """,
                ctx.guild.id,
                target.id,
                is_query=True,
                one_val=True
            )

            to_send = Embed(title="Removed user",
                            description=f"{esc_md(target.display_name)} removed from quotes - \n had {count} quotes on this server",
                            colour=ctx.author.colour
                        ).set_footer(
                            text=f"Removed by {esc_md(ctx.author.display_name)}",
                            icon_url=ctx.author.avatar_url
                        ).set_thumbnail(
                            url=member.avatar_url
                        )
        
            await ctx.send(embed=to_send)

    @quotes.command()
    async def add(self, ctx, quote: str, member: Member):

        target = member if member is not None else ctx.author
        
        await self.bot.db.execute(
        """UPDATE quotes
           SET quotes_array = quotes_array || $1
           WHERE guild_id = $2
           AND user_id = $3
        """,
        quote,
        ctx.guild.id,
        target.id
        )

        to_send = Embed(title="Added quote",
                        description=quote,
                        colour=target.colour
                       ).set_author(
                        name=esc_md(target.display_name), 
                        url=target.avatar_url
                       ).set_footer(
                        text=f"Added by {esc_md(ctx.author.display_name)}",
                        icon_url=ctx.author.avatar_url
                       )

        await ctx.send(embed=to_send)

    @quotes.command()
    async def remove(self, ctx: commands.Context, index: int, member: Member):
        target = member if member is not None else ctx.author
        
        removed = await self.bot.db.execute(
        """UPDATE quotes
           SET quotes_array = array_remove(quotes_array, quotes_array[$1])
           WHERE guild_id = $2
           and user_id = $3
           RETURNING quotes_array[$1]
        """,
        index,
        ctx.guild.id,
        target.id,
        is_query=True,
        one_val=True
        )

        to_send = Embed(title="Removed quote",
                        description=removed,
                        colour=target.colour
                       ).set_author(
                        name=esc_md(target.display_name), 
                        url=target.avatar_url
                       ).set_footer(
                        text=f"Removed by {esc_md(ctx.author.display_name)}",
                        icon_url=ctx.author.avatar_url
                       )
        
        await ctx.send(embed=to_send)

    @quotes.command()
    async def random(self, ctx: commands.Context, member: Member):
        target = member if member is not None else ctx.author
        
        quotes = await self.bot.db.execute(
            """SELECT quotes_array FROM quotes WHERE guild_id=$1 AND user_id=$2""",
            ctx.guild.id,
            target.id,
            is_query=True,
            one_val=True
        )

        quote = random.choice(quotes)

        to_send = Embed(title=f"Quote from {esc_md(target.display_name)}",
                        description=quote,
                        colour=target.colour
                        ).set_thumbnail(
                            url=target.avatar_url
                        ).set_footer(
                            text=f"Requested by {esc_md(ctx.author.display_name)}",
                            icon_url=ctx.author.avatar_url
                        )

        ctx.send(embed=to_send)


    @quotes.command()
    async def view(self, ctx, index: int, member: Member):
        target = member if member is not None else ctx.author
        
        quote = await self.bot.db.execute(
            """SELECT quotes_array[$1] FROM quotes WHERE guild_id=$2 AND user_id=$3""",
            index,
            ctx.guild.id,
            target.id,
            is_query=True,
            one_val=True
        )

        to_send = Embed(title=f"Quote from {esc_md(target.display_name)}",
                        description=quote,
                        colour=target.colour
                        ).set_thumbnail(
                            url=target.avatar_url
                        ).set_footer(
                            text=f"Requested by {esc_md(ctx.author.display_name)}",
                            icon_url=ctx.author.avatar_url
                        )
        
        ctx.send(embed=to_send)

    @quotes.command()
    async def userlist(self, ctx, member: Member):
        target = member if member is not None else ctx.author
        
        quotes = await self.bot.db.execute(
            """SELECT quotes_arr FROM quotes WHERE guild_id=$1 AND user_id=$2""",
            ctx.guild.id,
            target.id,
            is_query=True,
            one_col=True
        )

        for idx, quote in enumerate(quotes):
            quotes[idx] = f'"*{quote}*"' if len(quote) < 196 else f'"*{quote[:193]}...*"'

        to_send = Embed(title=f'Quotes from {esc_md(target.display_name)}',
                        colour=target.colour
                       ).set_thumbnail(
                           url=target.avatar_url
                       ).set_footer(
                           text=f'Requested by {esc_md(ctx.author.display_name)}',
                           icon_url=ctx.author.avatar_url
                       )
        
        pagination.send_pages(ctx, to_send, quotes)
        
   
    @quotes.command()
    async def serverlist(self, ctx):
        users = await self.bot.db.execute(
            """SELECT user_id FROM quotes where guild_id=$1""",
            ctx.guild.id,
            is_query=True,
            one_col=True)
        
        usernames = [esc_md(self.bot.get_user(user).display_name) for user in users]

        to_send = Embed(title=f'Users with quotes from {esc_md(ctx.guild.name)}',
                        colour=ctx.author.colour
                       ).set_thumbnail(
                           url=ctx.guild.avatar_url
                       ).set_footer(
                           text=f'Requested by {esc_md(ctx.author.display_name)}',
                           icon_url=ctx.author.avatar_url
                       )

        pagination.send_pages(ctx, to_send, usernames)

