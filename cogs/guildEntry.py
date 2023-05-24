import discord

from functions import welcome
from discord.ext import commands

class Greetings(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        channel = discord.utils.find(lambda c: 'welcome' in c.name, member.guild.text_channels)
        if channel is not None:
            await channel.send(f'{member.mention} {welcome()}')

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        channel = discord.utils.find(lambda c: 'welcome' in c.name, member.guild.text_channels)
        if channel is not None:
            await channel.send(f'{member} imagine leaving lmao, bye <:nail_care:886811404626165861>')

async def setup(bot: commands.Bot):
    await bot.add_cog(Greetings(bot))
