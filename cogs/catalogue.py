import asyncio
import aiohttp
from bot_helpers import pagination
from urllib.parse import urlparse, urlunparse
import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.utils import escape_markdown as esc_md
from typing import Literal


class Catalogue(commands.Cog, name="catalogue"):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()

    async def is_target_self(ctx):
        return not bool(ctx.message.mentions)

    def is_enabled():
        async def predicate(ctx):
            if ctx.message.raw_mentions != []:
                check_id = ctx.message.raw_mentions[0]
            else:
                check_id = ctx.author.id
            return ctx.bot.cache.catalogue_users.get(check_id, None)
        return commands.check(predicate)

    @app_commands.command(name = "enable", description="Enable catalogue functionality for yourself.")
    async def enable(self, interaction: discord.Interaction):
        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, catalogue_enabled)
                VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
                SET catalogue_enabled = excluded.catalogue_enabled
            """,
            str(interaction.user.id),
            True,
        )
        await interaction.response.send("Catalogue successfully enabled.")

    @app_commands.command(name = "disable", description="Disable catalogue functionality for yourself.")
    async def disable(self, interaction: discord.Interaction):
        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, catalogue_enabled)
                VALUES ($1 $2)
            ON CONFLICT (user_id) DO UPDATE
                SET catalogue_enabled = is_catalogue_enabled
            """,
            str(interaction.user.id),
            False,
        )
        await interaction.response.send("Catalogue successfully disabled.")

    @app_commands.command(name="recommendations", description="View a list of songs or albums recommended to you.")
    @app_commands.describe(
        member = "The member whose list of recommendations you would like to view.",
        type = "Which type of recommendations you would like to view, defaults to both songs and albums."
    )
    @is_enabled()
    async def view(self, interaction: discord.Interaction, member: discord.Member = None, type: Literal["track", "album"] = "type"):

        target = member if member is not None else interaction.user

        music_info = await self.bot.db.execute(
            """
            SELECT type, music_id, artists, name, added_by 
            FROM catalogue
            WHERE user_id = $1
            AND type = $2
            """,
            str(target.id),
            type,
            is_query=True,
        )

        unique_members = {record[4] for record in music_info}

        members = {
            member_id: await interaction.guild.fetch_member(int(member_id))
            for member_id in unique_members
        }

        urls = [
            urlunparse(
                [
                    "https",
                    "open.spotify.com",
                    f"/{record[0]}/{record[1]}",
                    None,
                    None,
                    None,
                ]
            )
            for record in music_info
        ]
        catalogue_items = [
            f'{i}. [{esc_md(", ".join(record[2]))} - {esc_md(record[3])}]({url}) | **{record[0]}** - Catalogued by: {esc_md(members[record[4]].display_name)}'
            for i, (record, url) in enumerate(zip(music_info, urls), 1)
        ]

        to_send = (
            discord.Embed(
                title=f"{esc_md(target.display_name)}'s Catalogue",
                description="",
                colour=target.colour,
            )
            .set_thumbnail(url=target.avatar_url)
            .set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar_url,
            )
        )
        if catalogue_items != []:
            await pagination.send_pages(interaction, to_send, catalogue_items)
        else:
            await interaction.response.send_message("Your catalogue is empty!", ephemeral=True)

    @app_commands.command(description="Check your catalogue for tracks/albums you have completed.")
    @commands.check(is_target_self)
    @is_enabled()
    async def check(self, interaction: discord.Interaction):
        tasks = []

        music_info = await self.bot.db.execute(
            """
            SELECT type, music_id, artists, name, added_by
            FROM catalogue
            WHERE user_id = $1
            AND approved = $2
            """,
            str(interaction.user.id),
            True,
            is_query=True,
        )

        members = {
            record[4]: await interaction.guild.fetch_member(int(record[4]))
            for record in music_info
        }

        for record in music_info:
            tasks.append(self.get_music_plays(ctx, *tuple(record)[:4]))

        playcounts = await asyncio.gather(*tasks)

        completed_items = [
            [*tuple(rec), count]
            for rec, count in zip(music_info, playcounts)
            if count != 0
        ]

        if completed_items != ():

            urls = [
                urlunparse(
                    [
                        "https",
                        "open.spotify.com",
                        f"/{item[0]}/{item[1]}",
                        None,
                        None,
                        None,
                    ]
                )
                for item in completed_items
            ]

            embed_items = [
                f'{i}. [{esc_md(", ".join(item[2]))} - {esc_md(item[3])}]({url}) - {item[5]} {"plays" if item[5] > 1 else "play"} | **{item[0]}** - Catalogued by: {esc_md(members[item[4]].display_name)}'
                for i, (item, url) in enumerate(zip(completed_items, urls), 1)
            ]

            [
                await self.bot.db.execute(
                    """
                    DELETE FROM catalogue
                    WHERE user_id = $1
                    AND music_id = $2
                    """,
                    str(interaction.user.id),
                    item[1],
                )
                for item in completed_items
            ]

            to_send = discord.Embed(
                title=f"{esc_md(interaction.author.display_name)}'s Completed items",
                description="",
                colour=interaction.user.colour,
            ).set_thumbnail(url=interaction.user.avatar_url)

            await pagination.send_pages(ctx, to_send, embed_items)

        else:
            await interaction.response.send_message(
                "You have not completed any of the items in your catalogue since the last check.", ephemeral=True
            )

    @app_commands.command(description="Recommend a song to another user.")
    @is_enabled()
    async def recommend(self, ctx, link: str, member: discord.Member):

        music_type, music_id = urlparse(link).path[1:].split("/", 2)

        name, artists, count = await self.get_music_info(music_type, music_id)
        image = await self.get_music_art(music_type, music_id)

        await self.bot.db.execute(
            """
            INSERT INTO catalogue (user_id, type, music_id, approved, artists, name, added_by, track_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, music_id) DO NOTHING
            """,
            str(member.id),
            music_type,
            music_id,
            False,
            artists,
            name,
            str(ctx.author.id),
            count,
        )

        

        to_send = (
            discord.Embed(
                title=f"Recommended {music_type}!",
                description=f'[{esc_md(", ".join(artists))} - {esc_md(name)}]({link}) | **{music_type}** - Recommended to: {esc_md(ctx.author.display_name)}',
                colour=ctx.author.colour,
            )
            .set_author(name=ctx.author.display_name, url=ctx.author.avatar_url)
            .set_image(url=image)
        )

        await ctx.send(embed=to_send)

    @app_commands.command(description="Save a song to your own catalogue.")
    @commands.check(is_target_self)
    @is_enabled()
    async def save(self, ctx, link: str):

        music_type, music_id = urlparse(link).path[1:].split("/", 1)
        name, artists, count = await self.get_music_info(music_type, music_id)
        image = await self.get_music_art(music_type, music_id)

        await self.bot.db.execute(
            """
            INSERT INTO catalogue (user_id, type, music_id, approved, artists, name, added_by, track_count)
                VALUES ($1, $2, $3, $4, $5, $6, $1, $7)
            ON CONFLICT (user_id, music_id) DO NOTHING
            """,
            str(ctx.author.id),
            music_type,
            music_id,
            True,
            artists,
            name,
            count,
        )

        to_send = (
            Embed(
                title=f"Saved {music_type}!",
                description=f'[{esc_md(", ".join(artists))} - {esc_md(name)}]({link}) | **{music_type}**',
                colour=ctx.author.colour,
            )
            .set_author(name=ctx.author.display_name, url=ctx.author.avatar_url)
            .set_image(url=image)
        )

        await ctx.send(embed=to_send)

    @app_commands.command(description="Approve a song that has been recommended to you.")
    @commands.check(is_target_self)
    async def approve(self, interaction: discord.Interaction, index: int):

        entry_id = await self.get_music_by_index(interaction, index, False)

        entry = await self.bot.db.execute(
            """
            UPDATE catalogue
            SET approved = $1
            WHERE user_id = $2
            AND music_id = $3
            RETURNING type, music_id, artists, name, added_by
            """,
            True,
            str(interaction.user.id),
            entry_id,
            is_query=True,
            one_row=True,
        )

        url = urlunparse(
            ["https", "open.spotify.com", f"{entry[0]}/{entry[1]}", None, None, None]
        )
        image = await self.get_music_art(entry[0], entry[1])

        member = await interaction.guild.fetch_member(entry[4])
        added_by = member.display_name

        to_send = (
            discord.Embed(
                title=f"Approved {entry[0]}!",
                description=f'[{esc_md(", ".join(entry[2]))} - {esc_md(entry[3])}]({url}) | **{entry[0]}** - Recommended by: {esc_md(added_by)}',
                colour=interaction.user.colour,
            )
            .set_author(name=interaction.user.display_name, url=interaction.user.avatar_url)
            .set_image(url=image)
        )

        await ctx.send(embed=to_send)

    @app_commands.command(aliases=["deny"], description="Remove item from catalogue. Use deny to remove from recommendations.")
    @commands.check(is_target_self)
    async def remove(self, ctx, index: int):

        entry_id = await self.get_music_by_index(
            ctx, index, ctx.invoked_with == "remove"
        )

        removed = await self.bot.db.execute(
            """
            DELETE FROM catalogue
            WHERE user_id = $1
            AND music_id = $2
            RETURNING type, music_id, artists, name, added_by
            """,
            str(ctx.author.id),
            entry_id,
            is_query=True,
            one_row=True,
        )

        url = urlunparse(
            [
                "https",
                "open.spotify.com",
                f"{removed[0]}/{removed[1]}",
                None,
                None,
                None,
            ]
        )
        image = await self.get_music_art(removed[0], removed[1])

        added_by = (
            await ctx.guild.fetch_member(removed[4])
            if int(removed[4]) != ctx.author.id
            else "You"
        )

        to_send = (
            Embed(
                title=f"Removed {removed[0]}!",
                description=f'[{esc_md(", ".join(removed[2]))} - {esc_md(removed[3])})]({url}) | **{removed[0]}** - Recommended by: {esc_md(added_by)}',
                colour=ctx.author.colour,
            )
            .set_author(name=ctx.author.display_name, url=ctx.author.avatar_url)
            .set_image(url=image)
        )

        await ctx.send(embed=to_send)

    async def get_music_info(self, music_type: str, id: str):
        if music_type == "track":
            track = await self.bot.spotify.track(id)
            artists = [artist.name for artist in track.artists]
            return track.name, artists, 1

        elif music_type == "album":
            album = await self.bot.spotify.album(id)
            artists = [artist.name for artist in album.artists]
            return album.name, artists, album.total_tracks

        else:
            pass

    async def get_music_art(self, music_type: str, id: str):
        if music_type == "track":
            track = await self.bot.spotify.track(id)
            return track.album.images[1].url
        elif music_type == "album":
            album = await self.bot.spotify.album(id)
            return album.images[1].url

    async def get_music_plays(self, interaction, music_type, music_id, artists, name):
        lastfm = self.bot.get_cog("lastfm")
        await lastfm.get_username(ctx)

        if music_type == "track":
            count = await lastfm.get_playcount(
                artists[0], name, music_type, ctx.lastfm_user
            )
            return int(count)

        elif music_type == "album":

            tracks = []
            tasks = []

            album = await self.bot.spotify.album_tracks(music_id)
            track_pages = self.bot.spotify.all_pages(album)

            async for page in track_pages:
                tracks.extend(page.items)

            for track in tracks:
                if track.duration_ms >= 30000: # Tracks that are under 30 seconds are not recorded as played by Spotify unless looped
                    tasks.append(
                        lastfm.get_playcount(
                            artists[0], track.name, "track", interaction.lastfm_user
                        )
                    )

            counts = await asyncio.gather(*tasks)
            counts = [int(count) for count in counts]
            return sum(counts) if 0 not in counts else 0

    async def get_music_by_index(self, ctx, index: int, approved: bool):
        return await self.bot.db.execute(
            """
            SELECT music_id
            FROM catalogue
            WHERE approved = $1
            AND user_id = $2
            LIMIT 1 OFFSET $3
            """,
            approved,
            str(ctx.author.id),
            index - 1,
            is_query=True,
            one_val=True,
        )


def setup(bot):
    bot.add_cog(Catalogue(bot))