import asyncio
import re
from typing import Literal
from urllib.parse import urlparse, urlunparse
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import escape_markdown as esc_md
from bot_helpers import pagination  # pylint: disable=import-error


def is_target_self():
    """
    Command check for certain commands that a user should only be able
    to use on themselves - e.g. disabling/enabling catalogue functionality
    """

    def predicate(interaction: discord.Interaction):
        return not bool(interaction.message.raw_mentions)

    return app_commands.check(predicate)


def is_enabled():
    """
    Command check to see if the target user of a command has the
    catalogue functionality enabled themselves - the target may be
    the user themselves
    """

    async def predicate(interaction: discord.Interaction):
        if interaction.message.raw_mentions != []:
            check_id = interaction.message.raw_mentions[0]
        else:
            check_id = interaction.user.id
        return interaction.client.cache.catalogue_users.get(check_id, None)

    return app_commands.check(predicate)


class Catalogue(commands.GroupCog, name="catalogue"):
    """
    Commands cog to handle users saving music to automatically check against
    Last.fm. Commands list is as follows:
    /enable
    /disable
    /view
    /save
    /recommend
    /approve
    /remove
    /approveall
    /clear
    /check
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="enable", description="Enable catalogue functionality for yourself."
    )
    async def enable(self, interaction: discord.Interaction):
        """Enable catalogue functionality for the current user."""
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
        await interaction.response.send_message(
            """Catalogue successfully enabled.""", ephemeral=True
        )

    @app_commands.command(
        name="disable", description="Disable catalogue functionality for yourself."
    )
    async def disable(self, interaction: discord.Interaction):
        """Disable catalogue functionality for the current user."""
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
        await interaction.response.send_message(
            """Catalogue successfully disabled. Anyone can still view your catalogue and you may
               recommend to other users, but you cannot save songs for yourself. 
               Other users cannot recommend to you either.""",
            ephemeral=True,
        )

    @app_commands.command(
        name="viewcatalogue",
        description="View the catalogue or waitlist for a given user.",
    )
    @app_commands.describe(
        member="The member whose catalogue you would like to view. Leave empty to view your own.",
        classification="Which type of recommendations you would like to view, defaults to both songs and albums if left empty.",
        approved="True to view all approved submissions, false otherwise. Defaults to true.",
    )
    async def view(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None,
        classification: Literal["track", "album"] = "type",
        approved: bool = True,
    ):
        """
        Command to allow users to view items saved to catalogue, categorized
        by approval status.
        """
        target = member if member is not None else interaction.user

        music_info = await self.bot.db.execute(
            """
            SELECT type, music_id, artists, name, added_by
            FROM catalogue
            WHERE user_id = $1
            AND type = $2
            AND approved = $3
            """,
            str(target.id),
            classification,
            approved,
            is_query=True,
        )

        if music_info != ():
            await self._send_as_embeds(interaction, music_info)
        else:
            await interaction.response.send_message(
                "Your catalogue is empty!", ephemeral=True
            )

    @app_commands.command(
        description="Check your catalogue for tracks/albums you have completed."
    )
    @is_target_self()
    @is_enabled()
    async def check(self, interaction: discord.Interaction):
        """
        Command to check for completed items, either from recommendations
        on self-saved.
        """
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

        for record in music_info:
            tasks.append(self._get_music_plays(interaction, *tuple(record)[:4]))

        playcounts = await asyncio.gather(*tasks)

        completed_items = [
            [*tuple(rec), count]
            for rec, count in zip(music_info, playcounts)
            if count != 0
        ]

        if completed_items != ():

            for item in completed_items:
                await self.bot.db.execute(
                    """
                    DELETE FROM catalogue
                    WHERE user_id = $1
                    AND music_id = $2
                    """,
                    str(interaction.user.id),
                    item[1],
                )
            await self._send_as_embeds(interaction, completed_items, removing=True)

        else:
            await interaction.response.send_message(
                "You have not completed any of the items in your catalogue since the last check.",
                ephemeral=True,
            )

    @app_commands.command(
        description="Recommend a song to another user. Please note that this only works with Spotify links."
    )
    @app_commands.describe(
        link="Spotify link to music/album to recommend.",
        member="The user you would like to recommend the song to.",
    )
    @is_enabled()
    async def recommend(
        self, interaction: discord.Interaction, link: str, member: discord.Member
    ):
        """
        Command for recommending music to other users.
        """
        if not self._is_spotify_link(link):
            await interaction.response.send("That is not a Spotify link!")
            return

        music_type, music_id = urlparse(link).path[1:].split("/", 2)

        name, artists, count = await self._get_music_info(music_type, music_id)
        image = await self._get_music_art(music_type, music_id)

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
            str(interaction.user.id),
            count,
        )

        to_send = (
            discord.Embed(
                title=f"Recommended {music_type}!",
                description=f'[{esc_md(", ".join(artists))} - {esc_md(name)}]({link}) | **{music_type}** - Recommended to: {esc_md(interaction.user.display_name)}',
                colour=interaction.user.colour,
            )
            .set_author(
                name=interaction.user.display_name, url=interaction.user.avatar_url
            )
            .set_image(url=image)
        )

        await interaction.response.send(embed=to_send)

    @app_commands.command(description="Save a song to your own catalogue.")
    @is_target_self()
    @is_enabled()
    async def save(self, interaction: discord.Interaction, link: str):
        """
        Command for a user to save music for themselves. Auto-approves submissions.
        """
        if not self._is_spotify_link(link):
            await interaction.response.send("That is not a Spotify link!")
            return

        music_type, music_id = urlparse(link).path[1:].split("/", 1)
        name, artists, count = await self._get_music_info(music_type, music_id)
        image = await self._get_music_art(music_type, music_id)

        await self.bot.db.execute(
            """
            INSERT INTO catalogue (user_id, type, music_id, approved, artists, name, added_by, track_count)
                VALUES ($1, $2, $3, $4, $5, $6, $1, $7)
            ON CONFLICT (user_id, music_id) DO NOTHING
            """,
            str(interaction.user.id),
            music_type,
            music_id,
            True,
            artists,
            name,
            count,
        )

        to_send = (
            discord.Embed(
                title=f"Saved {music_type}!",
                description=f'[{esc_md(", ".join(artists))} - {esc_md(name)}]({link}) | **{music_type}**',
                colour=interaction.user.colour,
            )
            .set_author(
                name=interaction.user.display_name, url=interaction.user.avatar_url
            )
            .set_image(url=image)
        )

        await interaction.response.send(embed=to_send)

    @app_commands.command(
        description="Approve a song that has been recommended to you."
    )
    @app_commands.describe(
        index="Which item would you like to approve, index relative to the view command."
    )
    @is_target_self()
    async def approve(self, interaction: discord.Interaction, index: int):
        """
        Allow a user to approve a recommendation to be saved to their main
        catalogue. Only manual approval is allowed due to usage considerations.
        """
        entry_id = await self._get_music_by_index(interaction, index, False)

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
        image = await self._get_music_art(entry[0], entry[1])

        member = await interaction.guild.fetch_member(entry[4])
        added_by = member.display_name

        to_send = (
            discord.Embed(
                title=f"Approved {entry[0]}!",
                description=f'[{esc_md(", ".join(entry[2]))} - {esc_md(entry[3])}]({url}) | **{entry[0]}** - Recommended by: {esc_md(added_by)}',
                colour=interaction.user.colour,
            )
            .set_author(
                name=interaction.user.display_name, url=interaction.user.avatar_url
            )
            .set_image(url=image)
        )

        await interaction.response.send_message(embed=to_send)

    @app_commands.command(description="Remove an item you have saved to the catalogue.")
    @app_commands.describe(
        index="The index of this item as seen in the view command.",
        approval="True if the item being removed was already approved, false to deny an unapproved item.",
    )
    @is_target_self()
    async def remove(
        self, interaction: discord.Interaction, index: int, approval: bool
    ):
        """
        Commanmd to remove a song from the catalogue.
        """
        entry_id = await self._get_music_by_index(interaction, index, approval)

        removed = await self.bot.db.execute(
            """
            DELETE FROM catalogue
            WHERE user_id = $1
            AND music_id = $2
            RETURNING type, music_id, artists, name, added_by
            """,
            str(interaction.user.id),
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
        image = await self._get_music_art(removed[0], removed[1])

        added_by = (
            await interaction.guild.fetch_member(removed[4])
            if int(removed[4]) != interaction.user.id
            else "You"
        )

        to_send = (
            discord.Embed(
                title=f"Removed {removed[0]}!",
                description=f'[{esc_md(", ".join(removed[2]))} - {esc_md(removed[3])})]({url}) | **{removed[0]}** - Recommended by: {esc_md(added_by)}',
                colour=interaction.user.colour,
            )
            .set_author(
                name=interaction.user.display_name, url=interaction.user.avatar_url
            )
            .set_image(url=image)
        )

        await interaction.response.send(embed=to_send)

    @app_commands.command(description="Approve all recommendations.")
    @is_target_self()
    async def approveall(self, interaction: discord.Interaction):
        """Function to approve all unapproved recommendations."""
        approved = await self.bot.db.execute(
            """
            UPDATE catalogue
            SET approved = $1
            WHERE user_id = $2
            AND approved IS DISTINCT FROM $1
            RETURNING type, music_id, artists, name, added_by
            """,
            True,
            str(interaction.user.id),
            is_query=True,
        )

        await self._send_as_embeds(interaction, approved)

    @app_commands.command(description="Clear the catalogue")
    @app_commands.describe(
        deleteall="True to clear entire catalogue, false to clear only unapproved submissions."
    )
    @is_target_self()
    async def clear(self, interaction: discord.Interaction, deleteall: bool):
        """Function to clear the entire catalogue."""
        to_remove = "approved" if deleteall else True
        removed = await self.bot.db.execute(
            """
            DELETE FROM catalogue
            WHERE user_id = $1
            AND approved = $2
            RETURNING type, music_id, artists, name, added_by
            """,
            str(interaction.user.id),
            to_remove,
            is_query=True,
        )

        if removed == ():
            await interaction.response.send_message(
                "Whatever you were trying to clear has already been cleared.",
                ephemeral=True,
            )
            return

        await self._send_as_embeds(interaction, removed, removing=True)

    async def _get_music_info(
        self, music_type: Literal["track", "album"], identifier: str
    ):
        """Use the Spotify API to retreive track names and artists."""
        if music_type == "track":
            track = await self.bot.spotify.track(id)
            artists = [artist.name for artist in track.artists]
            return track.name, artists, 1

        if music_type == "album":
            album = await self.bot.spotify.album(identifier)
            artists = [artist.name for artist in album.artists]
            return album.name, artists, album.total_tracks

    async def _get_music_art(
        self, music_type: Literal["album", "track"], identifier: str
    ):
        """Use the Spotify API to retrieve the cover art for a given single or album."""
        if music_type == "track":
            track = await self.bot.spotify.track(identifier)
            return track.album.images[1].url
        if music_type == "album":
            album = await self.bot.spotify.album(identifier)
            return album.images[1].url

    async def _get_music_plays(
        self,
        interaction: discord.Interaction,
        music_type: Literal["album", "track"],
        music_id,
        artists,
        name,
    ):
        """Use the Last.fm API to retrieve play data based on Spotify information."""
        lastfm = self.bot.get_cog("lastfm")
        await lastfm.get_username(interaction)

        if music_type == "track":
            count = await lastfm.get_playcount(
                artists[0], name, music_type, interaction.lastfm_user
            )
            return int(count)

        if music_type == "album":

            tracks = []
            tasks = []

            album = await self.bot.spotify.album_tracks(music_id)
            track_pages = self.bot.spotify.all_pages(album)

            async for page in track_pages:
                tracks.extend(page.items)

            for track in tracks:
                if (
                    track.duration_ms >= 30000
                ):  # Tracks that are under 30 seconds are not recorded as played by Spotify unless looped
                    tasks.append(
                        lastfm.get_playcount(
                            artists[0], track.name, "track", interaction.lastfm_user
                        )
                    )

            counts = await asyncio.gather(*tasks)
            counts = [int(count) for count in counts]
            return sum(counts) if 0 not in counts else 0

    async def _get_music_by_index(
        self, interaction: discord.Interaction, index: int, approved: bool
    ):
        """Retrieve item at a specific offset from the PostgreSQL database"""
        return await self.bot.db.execute(
            """
            SELECT music_id
            FROM catalogue
            WHERE approved = $1
            AND user_id = $2
            LIMIT 1 OFFSET $3
            """,
            approved,
            str(interaction.user.id),
            index - 1,
            is_query=True,
            one_val=True,
        )

    def _is_spotify_link(self, link: str) -> bool:
        """
        Additional link format checking - bot only supports Spotify links
        currently for data consistency reasons
        """
        parsed = urlparse(link)
        musictype, identifier = parsed.path.split("/", 2)
        return (
            parsed.netloc == "open.spotify.com"
            and musictype in ("track", "album")
            and len(identifier) == 22
            and re.match("^[a-zA-Z0-9]*$", identifier)
        )

    async def _send_as_embeds(
        self,
        interaction: discord.Interaction,
        records,
        removing: bool = False,
        completing: bool = False,
    ) -> bool:
        """
        Build embeds based on music items to be marked as removed, completed or for simple viewing.
        Embed titles vary based on command invocation - notify users using 'preceding'.
        Send all embeds using the pagination module.
        """
        unique_members = {record[4] for record in records}

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
            for record in records
        ]

        catalogue_items = [
            f'{i}. [{esc_md(", ".join(record[2]))} - {esc_md(record[3])}]({url}) | **{record[0]}** - Catalogued by: {esc_md(members[record[4]].display_name)}'
            for i, (record, url) in enumerate(zip(records, urls), 1)
        ]

        preceding = (
            "Removed from " if removing else "Completed in " if completing else ""
        )
        to_send = (
            discord.Embed(
                title=f"{preceding}{esc_md(interaction.user.display_name)}'s Catalogue",
                description="",
                colour=interaction.user.colour,
            )
            .set_thumbnail(url=interaction.user.avatar_url)
            .set_footer(
                text=f"Requested by {interaction.user.display_name}",
                icon_url=interaction.user.avatar_url,
            )
        )

        await pagination.send_pages(interaction, to_send, catalogue_items)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Catalogue(bot))
