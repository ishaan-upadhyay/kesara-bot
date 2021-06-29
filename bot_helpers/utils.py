import discord
from discord.ext import commands

def get_prefix(bot, message):
    if message.guild:
        prefix = bot.cache.prefixes.get(str(message.guild.id))
        return commands.when_mentioned_or()
    else:
        return commands.when_mentioned_or('$')
