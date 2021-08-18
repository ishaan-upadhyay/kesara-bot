from discord.ext import commands
class Owner(commands.Cog, name="owner"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.group(case_insensitive=True)
    async def owner(self, ctx):
        pass

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @owner.command()
    async def logout(self, ctx):
        print("========================================")
        print("Logging out.")
        await ctx.send("Logging out.")
        await self.bot.close()

def setup(bot):
    bot.add_cog(Owner(bot))