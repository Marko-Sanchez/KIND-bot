import discord
import asyncio
from discord.ext import commands

class DeletionCommands(commands.Cog):

    helpd = "Deletes callers previous mesagges by a specified amount\n dd (number)"
    helpD = "Deletes a specified or all previous users messages in a channel:\n DD (number) or DD (number) @user"


    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Deletes users most recent messages, sleeps to avoid rate limit.
    @commands.command(help=helpd)
    async def dd(self, context, amount:int = 0):
        if amount == 0 or amount > 20:
            return

        deleted = 0
        # Search channel history and delete user messages up to 'amount':
        async for msg in context.channel.history(limit=50):
            if msg.author == context.author:
                deleted +=1
                await asyncio.sleep(0.5)
                await msg.delete()

            if deleted > amount:
                return

    # Command deletes all or a specified users messages.
    # Throws: BadArgument and MissingPermissions errors.
    # Optional arguements {amount}, {member}.
    # amount: of messages to delete, member: members message to delete.
    @commands.command(help=helpD)
    @commands.has_permissions(manage_messages = True)
    async def DD(self, context, amount: int = 0, member: discord.Member = None):
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
            await context.send(f'Make sure to pass in a integer, for example: {context.prefix}dd 2')


    @DD.error
    async def DD_error(self, context, error):
        if isinstance(error, commands.BadArgument):
            await context.send(f'Make sure to pass in a correct format example: {context.prefix}DD 2 or {context.prefix}DD 4 @USER')
        elif isinstance(error, commands.MissingPermissions):
            return

def setup(bot: commands.Bot):
    bot.add_cog(DeletionCommands(bot))
