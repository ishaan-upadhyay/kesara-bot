import os
import discord
from discord.ext import commands
import random
import sys
from dotenv import load_dotenv

load_dotenv(verbose = True)

TOKEN=os.getenv("TOKEN")
COMMAND_PREFIX=os.getenv("PREFIX")

async def get_prefixes(bot, message):
    with message.guild as guild:
        if guild:
            return None
        else:
            return COMMAND_PREFIX

bot = commands.Bot(get_prefixes, )

@bot.event
async def on_ready():
    print('Successfully logged in as {0.user}!'.format(bot.user))
    print('========================================')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot: 
        return
    
    bot.process_commands(message)

bot.run(TOKEN)