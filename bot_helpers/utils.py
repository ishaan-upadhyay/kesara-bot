from discord import Embed
from discord.ext import commands

def get_prefix(bot, message):
    if message.guild:
        prefix = bot.cache.prefixes.get(str(message.guild.id), ';')
        return commands.when_mentioned_or(prefix)(bot, message)
    else:
        return commands.when_mentioned_or(';')(bot, message)
