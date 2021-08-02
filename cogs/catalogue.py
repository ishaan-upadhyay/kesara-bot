import asyncio
import aiohttp
from bot_helpers import pagination
from urllib.parse import urlparse, urlunparse
from discord.utils import escape_markdown as esc_md
from discord import Embed
from discord.ext import commands

class Catalogue(commands.Cog, name='catalogue'):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def is_target_self(self, ctx):
        return not bool(ctx.message.mentions)

    def is_enabled(self, ctx):
        async def predicate(ctx):
            return await self.bot.cache.catalogue_users.get(ctx.author.id)
    
    @commands.group(case_insensitive=True)
    async def catalogue(self, ctx):
        pass
    
    @catalogue.command()
    @commands.check(is_target_self)
    async def enable(self, ctx):
        
        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, catalogue_enabled)
                VALUES ($1 $2)
            ON CONFLICT (user_id) DO UPDATE
                SET catalogue = excluded.catalogue_enabled
            """,
            ctx.author,
            True
        )

    async def disable(self, ctx):

        await self.bot.db.execute(
            """
            INSERT INTO users (user_id, is_catalogue_enabled)
                VALUES ($1 $2)
            ON CONFLICT (user_id) DO UPDATE
                SET catalogue = excluded.is_catalogue_enabled
            """,
            ctx.author,
            False
        )

    @catalogue.command(aliases=['recs', 'recsview', 'recommendations'])   
    @is_enabled()
    async def view(self, ctx, member=None):
        
        approval_status = ctx.invoked_with() in ['recs', 'recsview', 'recommendations']
        target = member if member is not None else ctx.author

        music_info = await self.bot.db.execute(
            """
            SELECT type, music_id, artists, name, recommended_by 
            FROM catalogue
            WHERE user_id = $1
            AND approved = $2
            """,
            target.id,
            approval_status,
            is_query=True
        )

        url_base = ['https', 'open.spotify.com']

        urls = [urlunparse(url_base.append(f'/{record[0]}/{record[1]}')) for record in music_info]
        catalogue_items = [f'{i}. [{(", ".join(record[2]))} - {record[3]}]({url}) | **{record[0]}**' 
                           for i, (record, url) 
                           in enumerate(zip(music_info, urls))]

        to_send = Embed(title=f"{esc_md(target.display_name)}'s Catalogue",
                        description='',
                        colour=target.colour    
                        ).set_thumbnail(
                            url=target.avatar_url
                        ).set_footer(
                            text=f'Requested by {ctx.author.display_name}',
                            icon_url = ctx.author.avatar_url
                        )
        
        await pagination.send_pages(ctx, to_send, catalogue_items)

    @catalogue.command('check')
    @commands.check(is_target_self)
    async def check(self, ctx):
        tasks = []
        
        music_info = await self.bot.db.execute(
            """
            SELECT type, music_id, artists, name
            FROM catalogue
            WHERE user_id = $1
            """,
            ctx.author.id,
            is_query = True
        )

        for record in music_info:
            tasks.append(self.get_music_plays(ctx, *tuple(record)))

        playcounts = asyncio.gather(*tasks)
        completed_items = [[*tuple(rec), count] for rec, count in zip(music_info, playcounts) if count != 0]

        if completed_items:
            url_base = ['https', 'open.spotify.com']
            urls = [urlunparse(url_base.append(f'/{item[0]}/{item[1]}')) for item in completed_items]

            embed_items = [f'{i}. [{", ".join(item[2])} - {item[3]}]({url}) - {item[4]} plays | **{item[0]}**' 
                        for i, (item, url) 
                        in enumerate(zip(completed_items, urls))]

            to_send = Embed(title=f"{esc_md(ctx.author.display_name)}'s Completed items",
                            description='',
                            colour=ctx.author.colour    
                            ).set_thumbnail(
                                url=ctx.author.avatar_url
                            )
            
            await pagination.send_pages(ctx, to_send, embed_items)
        
        else:
            await ctx.send("")

    @catalogue.command()
    async def recommend(self, ctx, link:str, member):

        music_type, music_id = urlparse(link).path.split('/', 1)
        name, artists = await self.get_music_info(music_type, music_id)

        await self.bot.db.execute(
            """
            INSERT INTO catalogue (user_id, type, music_id, approved, artists, name, added_by)
                VALUES ($1 $2 $3 $4 $5 $6 $7)
            ON CONFLICT (music_id) DO NOTHING
            """,
            member.id,
            music_type,
            music_id,
            False,
            name,
            artists,
            ctx.author.id)
    
    @catalogue.command('save')
    @commands.check(is_target_self)
    @is_enabled()
    async def save(self, ctx, link: str):
        
        music_type, music_id = urlparse(link).path.split('/', 1)
        name, artists = await self.get_music_info(music_type, music_id)

        await self.bot.db.execute(
            """
            INSERT INTO catalogue (user_id, type, music_id, approved, artists, name, added_by)
                VALUES ($1 $2 $3 $4 $5 $6 $1)
            ON CONFLICT (music_id) DO NOTHING
            """,
            ctx.author.id,
            music_type,
            music_id,
            True,
            name,
            artists)

        to_send = Embed(title="Saved song!",
                        description=f""

        )

    @catalogue.command('remove')
    @commands.check(is_target_self)
    @is_enabled()
    async def remove(self, ctx, link: str=None, music_info: str=None):
        
        if music_info is not None:
            name, artist = music_info.split('-', 1)
            deleted = await self.bot.db.execute(
                """DELETE FROM catalogue
                WHERE name = $1
                AND artist = $2
                AND user_id = $3
                RETURNING type, music_id
                """,
                name,
                artist,
                ctx.author.id,
                is_query=True,
                one_row=True
            )

        elif link is not None:
            music_id = urlparse(link).path.split('/', 1)[1]
            await self.bot.db.execute(
                """DELETE FROM catalogue
                WHERE music_id = $1
                AND user_id = $2
                """,
                music_id,
                ctx.author.id,
            )

        else:
            pass

    async def get_music_info(self, music_type: str, id: str):        
        if music_type == 'track':
            track = self.bot.spotify.track(id)
            artists = [artist.name async for artist in track.artists]
            return track.name, artists
        
        elif music_type == 'album':
            album = self.bot.spotify.album(id)
            artists = [artist.name async for artist in album.artists]
            return album.name, artists
        
        else:
            pass

    async def get_music_plays(self, ctx, music_type, music_id, artists, name):
        lastfm = self.bot.get_cog('lastfm')
        await lastfm.get_username(ctx)
        
        if music_type == 'track':
            count = lastfm.get_playcount(artists[0], name, music_type, ctx.target)
            return count
        
        elif music_type == 'album':

            tracks = []
            tasks = []

            album = self.bot.spotify.album_tracks(music_id)
            track_pages = self.bot.spotify.all_tracks(album)
            
            for page in track_pages:
                tracks.extend(page.items)

            for track in tracks:
                tasks.append(lastfm.get_playcount(artists[0], track.name, 'track', ctx.target))
            
            counts = asyncio.gather(*tasks)
            return sum(counts) if 0 not in counts else 0
