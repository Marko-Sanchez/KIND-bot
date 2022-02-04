import discord
import asyncio
from discord.ext import commands

class DeletionCommands(commands.Cog):

    helpd = "Deletes callers message takes a amount, default value (3):\n dd (number)"
    helpD = "Command deletes specified or non-specified users messages in a channel:\n DD (number) or DD (number) @user"


    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Deletes users most recent messages, sleeps to avoid rate limit.
    @commands.command(help=helpd)
    async def dd(self, context, amount:int = 3):
        if amount == 0 or amount > 20:
            return

        deleted = 0
        # Search channel history an delete user messages up to 'amount':
        async for msg in context.channel.history(limit=50):
            if msg.author == context.author:
                deleted +=1
                await asyncio.sleep(0.5)
                await msg.delete()

            if deleted > amount:
                return

    # Amount: of messages to delete, member: members message to delete.
    @commands.command(help=helpD)
    @commands.has_permissions(administrator=True)
    async def DD(self, context, amount: int = 3, member: discord.Member = None):
        if member is None:
            await context.channel.purge(limit = amount + 1)
        else:
            if amount == 0 or amount > 20:
                return

            deleted = 0
            # Search channel history an delete members messages up to 'amount':
            async for msg in context.channel.history(limit=50):
                if member == msg.author:
                    deleted += 1
                    await asyncio.sleep(0.5)
                    await msg.delete()

                if deleted > amount:
                    return
    @dd.error
    async def dd_error(self, context, error):
        if isinstance(error, commands.BadArgument):
            await context.send('Make sure to pass in a integer example: !dd 2')


    @DD.error
    async def DD_error(self, context, error):
        if isinstance(error, commands.BadArgument):
            await context.send('Make sure to pass in a correct format example: !DD 2 or !DD 4 @USER')
        elif isinstance(error, commands.MissingPermissions):
            return

def setup(bot: commands.Bot):
    bot.add_cog(DeletionCommands(bot))
