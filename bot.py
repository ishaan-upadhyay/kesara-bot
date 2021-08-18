import os
import discord
import asyncio
from discord.ext import commands
import random
import sys
import traceback
import tekore as tk
from dotenv import load_dotenv
from tekore._client.api import track
from bot_helpers.utils import get_prefix  # pylint=disable-import-error
from bot_helpers.cache import BotCache
from bot_helpers.postgres import Postgres


load_dotenv(verbose=True)

TOKEN = os.getenv("TOKEN")
COMMAND_PREFIX = os.getenv("PREFIX")
SPOTIFY_TOKEN = os.getenv("SPOT_TOKEN")
SPOTIFY_SECRET = os.getenv("SPOT_SECRET")

class KesaraBot(commands.Bot):
    def __init__(self, **kwargs):
        self.cache = BotCache(self)
        self.db = Postgres(self)
        asyncio.get_event_loop().run_until_complete(self.db.init_pool())
        spot_token = tk.request_client_token(SPOTIFY_TOKEN, SPOTIFY_SECRET)
        self.spotify = tk.Spotify(spot_token, asynchronous=True)
        super().__init__(**kwargs)

    async def close(self):
        await self.db.close_pool()
        await self.spotify.close()
        await super().close()

bot = KesaraBot(command_prefix=get_prefix, owner_id=291666852533501952)

@bot.event
async def on_ready():
    print("Successfully logged in as {0}!".format(bot.user.name))
    print("========================================")


@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    await bot.process_commands(message)


extensions = [
    "quotes",
    "lastfm",
    "catalogue",
    "owner"
]

if __name__ == "__main__":
    print("Is main")
    for extension in extensions:
        print(extension)
        try:
            bot.load_extension(f"cogs.{extension}")
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(e)
            traceback.print_exc()
            print("Could not load extension")

bot.run(TOKEN)
