import os
import discord
import requests
from datetime import datetime
from discord.ext import commands


class WorldOfTanks(commands.Cog):

    """
    Local cache to store user name and ID:
    Using the callers id as a key.
    containing fields:
        author_id : { "account_id":int, "name":str, "wins":int, "total_battles":int, "datetime":datetime}

    account_id: Users wargaming account ID.
    name: Users name in world of tanks blitz.
    wins: lifetime wins.
    total_battles: lifetime battles played.
    datetime: Date user was added to cache.
    """
    userInfo = {}

    iam_help = "Start tracking your WOTB stats!\nBy passing in your WG account name:\niam (username)"
    stats_help = "Displays overall statistics and daily statistics"
    api_query_user = 'https://api.wotblitz.com/wotb/account/list/?application_id={0}&search={1}'
    api_query_stats = 'https://api.wotblitz.com/wotb/account/info/?account_id={0}&application_id={1}'
    WOTB_APP_ID = os.environ.get('WOTB_APP_ID')

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Store Api request information in cache to be used as base plate to
    # calculate statistics for the day.
    async def cache(self, author_id, accountID, userStats):
        self.userInfo[author_id] = {}
        self.userInfo[author_id]["name"] = userStats["nickname"]
        self.userInfo[author_id]["total_battles"] = userStats["statistics"]["all"]["battles"]
        self.userInfo[author_id]["wins"] = userStats["statistics"]["all"]["wins"]
        self.userInfo[author_id]["account_id"] = accountID
        self.userInfo[author_id]["datetime"] = datetime.utcnow().isoformat(' ','seconds')

    # Grabs users statistics from wotb api, caches it, and stores users:
    # account_id, nickname in database for future retrieval.
    @commands.command(help=iam_help)
    async def iam(self, context, wotbName:str = None):

        author_id = str(context.author.id)
        if wotbName is None:
            await context.send("Make sure to pass in arguements")
            await context.invoke(self.bot.get_command("help"),"iam")
            return
        elif author_id in self.userInfo:
            await context.send("User is already being watched")
            return

        # Processing visual:
        await context.trigger_typing()

        # Query wargaming Api for user:
        req = requests.get(self.api_query_user.format(self.WOTB_APP_ID, wotbName)).json()

        # If meta count is greater then one or == 0, means a list was returned and users name should be more specific:
        if req["meta"]["count"] == 0 or req["meta"]["count"] > 1:
            await context.send("Make sure you have passed in the correct name")
            return

        accountID = str(req["data"][0]["account_id"])

        # Query user stats and store in cache:
        stats = requests.get(self.api_query_stats.format(accountID, self.WOTB_APP_ID)).json()
        await self.cache(author_id, accountID, stats["data"][accountID])

        await context.send(f'Account for {self.userInfo[author_id]["name"]} has been added and now being watched')

    # Displays users daily win-ratio
    @commands.command(help=stats_help)
    async def stats(self, context):

        author_id = str(context.author.id)
        if author_id not in self.userInfo:
            await context.send("User is not being watched, to begin watching use iam command")
            await context.invoke(self.bot.get_command("help"),"iam")
            return

        # Processing visual:
        await context.trigger_typing()

        accountID = self.userInfo[author_id]["account_id"]
        stats = requests.get(self.api_query_stats.format(accountID, self.WOTB_APP_ID)).json()

        # Calculate overall win ratio:
        new_total_battles = stats["data"][accountID]["statistics"]["all"]["battles"]
        new_wins = stats["data"][accountID]["statistics"]["all"]["wins"]
        overall_wr = "{:.2f}".format((new_wins / new_total_battles)* 100)

        # Calculate daily win ratio:
        old_total_battles = self.userInfo[author_id]["total_battles"]
        old_wins = self.userInfo[author_id]["wins"]

        daily_wr = 0
        battle_diff = new_total_battles - old_total_battles
        if battle_diff != 0:
            daily_wr = "{:.2f}".format(((new_wins - old_wins) / battle_diff)* 100)

        # Color code based on win-ratio:
        color = 0xcad1c7
        if 50 <= float(daily_wr) < 55:
            color = 0x71ba47
        elif 55 <= float(daily_wr) < 60:
            color = 0x318004
        elif 60 <= float(daily_wr) < 65:
            color = 0x146bb8
        elif float(daily_wr) >= 65:
            color = 0x5d11bf

        # Create Embed:
        embed = discord.Embed(
            title = f'{self.userInfo[author_id]["name"]} statistics',
            colour = color
        )

        embed.set_thumbnail(url=context.author.avatar_url)

        time = datetime.fromtimestamp(stats["data"][accountID]["last_battle_time"])
        embed.set_footer(text=f'from: {self.userInfo[author_id]["datetime"]}  to: {time}')

        embed.add_field(
            name = f'Overall win-ratio: {overall_wr}%',
            value = "-------------------------------",
            inline=False
        )

        if float(daily_wr) != 0:
            embed.add_field(
                name = f'Daily win-ratio: {daily_wr}%',
                value = "-------------------------------",
                inline=False
            )
        await context.send(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(WorldOfTanks(bot))
