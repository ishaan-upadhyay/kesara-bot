import os
import discord
from discord.ext import commands
import random
import sys
from dotenv import load_dotenv
from bot_helpers.utils import get_prefix # pylint=disable-import-error
from bot_helpers.cache import BotCache
from bot_helpers.postgres import Postgres


load_dotenv(verbose = True)

TOKEN=os.getenv("TOKEN")
COMMAND_PREFIX=os.getenv("PREFIX")

bot = commands.Bot(command_prefix=get_prefix, owner_id=291666852533501952)
bot.cache = BotCache(bot)
bot.db = Postgres(bot)

@bot.event
async def on_ready():
    print('Successfully logged in as {0}!'.format(bot.user.name))
    print('========================================')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot: 
        return
    
    await bot.process_commands(message)

extensions = [
    "quotes",
    #"lastfm",
    #"catalogue"
]

if __name__ == '__main__':
    print('Is main')
    for extension in extensions:
        print(extension)
        try:
            bot.load_extension(f'cogs.{extension}')
            print(f'Loaded extension: {extension}')
        except Exception:
            print('Could not load extension')

bot.run(TOKEN)