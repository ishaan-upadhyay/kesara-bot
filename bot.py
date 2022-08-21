import os
from dotenv import load_dotenv
import discord
import asyncio
from discord.ext import commands
import traceback
import tekore as tk
from bot_helpers.cache import BotCache
from bot_helpers.postgres import Postgres


load_dotenv(verbose=True)

TOKEN = os.getenv("TOKEN")
SPOTIFY_TOKEN = os.getenv("SPOT_TOKEN")
SPOTIFY_SECRET = os.getenv("SPOT_SECRET")
DEBUG_GUILD = os.getenv("DEBUG_GUILD")

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

bot = KesaraBot(owner_id=291666852533501952, debug_guilds=[DEBUG_GUILD])

@bot.event
async def on_ready():
    print("Successfully logged in as {0}!".format(bot.user.name))
    print("========================================")

@bot.event
async def on_application_command(ctx):
    if ctx.interaction.user == bot.user or ctx.interaction.user.bot:
        return

    await bot.process_application_commands(ctx)

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