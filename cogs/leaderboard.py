import discord
import pymongo
from datetime import datetime

from discord import app_commands
from discord.ext import commands

class LeaderBoard(commands.GroupCog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    """
        Pull the top 5 chatters from the mongo database and display them in a nice embed.
    """
    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(name="top5", description="Shows top 5 chatters")
    async def top5(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title = 'Top 5 Chatters',
            colour = 0xaa6ca3,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="\U0001F499 Be Kind")
        file = discord.File("images/ribbon.png", filename="ribbon.png")
        embed.set_thumbnail(url="attachment://ribbon.png")

        guildID = str(interaction.guild_id)
        for user in self.bot.DB.levels.find({guildID : {"$exists": True}}).sort(f"{guildID}.user_info.exp", pymongo.DESCENDING).limit(5):
            username = await self.bot.fetch_user(user["_id"])
            embed.add_field(
                name=username.name,
                value=f"Level: {user[guildID]['user_info']['level']}",
                inline=False
            )

        await interaction.response.send_message(file=file, embed=embed)

    """
        Error handling for the top5 command.
    """
    @top5.error
    async def top5_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message("Please wait a couple seconds before using this command again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occured: {str(error)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderBoard(bot))
