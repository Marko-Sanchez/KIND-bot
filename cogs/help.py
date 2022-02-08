import discord
from datetime import datetime
from discord.ext import commands

class HelpCommand(commands.Cog):

    helpStr = "Displays this menu, displays arguements information"
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(help=helpStr)
    async def help(self, context, command_name = None):
        embed = discord.Embed(
            title = 'Bot Commands',
            colour = 0xaa6ca3,
            timestamp=datetime.utcnow()
        )

        # Embed Beautifiers:
        file = discord.File("images/settings.png", filename="settings.png")
        embed.set_thumbnail(url="attachment://settings.png")
        embed.set_footer(text="\U0001F499 Be Kind")

        commandsList = [x.name for x in self.bot.commands]
        if command_name is None:
            # Show the current server prefix:
            embed.add_field(
                name="Server Prefix",
                value=context.prefix,
                inline=False
            )

            for command in self.bot.commands:
                embed.add_field(
                    name= context.prefix + command.name,
                    value=command.help + "\n------------------------------",
                    inline=False
                )
        elif command_name in commandsList:
            embed.add_field(
                name=command_name,
                value=self.bot.get_command(command_name).help
            )
        else:
            await context.send("Sorry that command does not exist, make sure you spelled it correctly", delete_after=30.0)
            return

        await context.send(file=file, embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(HelpCommand(bot))
