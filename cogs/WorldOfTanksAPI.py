import os
import discord
import requests
from datetime import datetime, timezone, timedelta
from discord.ext import tasks, commands
from enum import Enum

class Color(Enum):
    defualt = 0x2d4357
    lightGreen = 0x71ba47
    darkGreen = 0x318004
    blue = 0x146bb8
    purple = 0x5d11bf

class WorldOfTanks(commands.Cog):

    """
    Local cache to store user name and ID:
    Using the callers id as a key.
    containing fields:
        author_id : { "account_id":string, "name":str, "wins":int, "total_battles":int, "datetime":datetime}

    account_id: Users wargaming account ID.
    name: Users name in world of tanks blitz.
    wins: lifetime wins.
    total_battles: lifetime battles played.
    datetime: Date user was added to cache.
    """
    userCache = {}

    iam_help = "Start tracking your WOTB stats!\nBy passing in your WG account name:\niam (username)"
    stats_help = "Displays overall statistics and daily statistics"
    api_query_user = 'https://api.wotblitz.com/wotb/account/list/?application_id={0}&search={1}'
    api_query_stats = 'https://api.wotblitz.com/wotb/account/info/?account_id={0}&application_id={1}'

    WOTB_APP_ID = os.environ.get('WOTB_APP_ID')

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_start_up())
        self.morningTask.start()

    """
        Store Api request information in cache to be used as base plate to
        calculate statistics of the day.

        @params:
                author_id{string} users unique discord ID.
                accountID{string} users wargaming account ID.
                userStats{dictionary} contains users statistics pulled from wargaming API.
    """
    async def cache(self, author_id, accountID, userStats):
        self.userCache[author_id] = {}
        self.userCache[author_id]["name"] = userStats["nickname"]
        self.userCache[author_id]["total_battles"] = userStats["statistics"]["all"]["battles"]
        self.userCache[author_id]["wins"] = userStats["statistics"]["all"]["wins"]
        self.userCache[author_id]["account_id"] = accountID

        # Pacific Standard Time for Los Angeles (UTC−07:00)
        timezone_offset = -7.0
        tzinfo = timezone(timedelta(hours=timezone_offset))
        now = datetime.now(tzinfo)

        # Set time of cached data, to local Los Angeles time:
        self.userCache[author_id]["datetime"] = now.strftime("%b-%-d-%Y %-I:%M %p")


    """
        Iterate through all registered players in server and add there latest statistics to cache and database.
    """
    async def reloadCache(self):

        # Grab all servers with "playerAccounts" field:
        projection = {"playerAccounts": 1}
        servers = self.bot.DB.servers.find({"playerAccounts": { "$exists": True}}, projection)

        # Iterate through player list, grab player info, and query wargaming API:
        for playerList in servers:
            for _, id in playerList["playerAccounts"]:

                # Grab user stats from database:
                userStats = self.bot.DB.levels.find_one({"_id": int(id)}, {"userstats": 1})

                if userStats is None or "userstats" not in userStats:
                    continue

                # Add back into cache:
                self.userCache[id] = userStats["userstats"]


    """
        When bot goes online, load player information onto cache
    """
    async def on_start_up(self):
        await self.bot.wait_until_ready()
        await self.reloadCache()

    """
        Every morning at 9am PST pull latest user statistics and add to cache.
    """
    @tasks.loop(hours=24)
    async def morningTask(self):

        # Grab all servers with "playerAccounts" field:
        projection = {"playerAccounts": 1}
        servers = self.bot.DB.servers.find({"playerAccounts": { "$exists": True}}, projection)

        # Iterate through player list, grab player info, and query wargaming API:
        for playerList in servers:
            for wotbName, id in playerList["playerAccounts"]:

                # Query wargaming Api for user account:
                req = requests.get(self.api_query_user.format(self.WOTB_APP_ID, wotbName)).json()

                # Grab wargaming ID:
                accountID = str(req["data"][0]["account_id"])

                # Query wargaming API for user statistics:
                stats = requests.get(self.api_query_stats.format(accountID, self.WOTB_APP_ID)).json()
                await self.cache(id, accountID, stats["data"][accountID])

                # Add latest user statistics to MongoDB:
                self.bot.DB.levels.update_one({"_id":int(id)}, {"$set": {"userstats": self.userCache[id]} }, upsert=True)


    """
        Function called before 'morningTask' executes to make sure task is called
        at 9am. Sleeps until 9am PST occurs.
    """
    @morningTask.before_loop
    async def wait_until_9am(self):

        timezone_offset = -7.0  # Pacific Standard Time for Los Angeles (UTC−07:00)
        tzinfo = timezone(timedelta(hours=timezone_offset))

        now = datetime.now(tzinfo) # Get the current time
        next_run = now.replace(hour=9, minute=0, second=0) # get local time of what would be 9am

        # If 9am is less then current time, then we have to wait till next morning to execute task:
        if next_run < now:
            next_run += timedelta(days=1)

        await discord.utils.sleep_until(next_run)


    """
        Stores first time callers account information from wargamming onto MongoDB database.
        Querys callers account and statistics from wargamming api, then caches information,
        finally adding account name to servers list of players whom have registered.

        @params:    wotbName{string} users in game name for world of tanks blitz.
    """
    @commands.command(help=iam_help)
    async def iam(self, context, wotbName:str = None):

        author_id = str(context.author.id)

        if wotbName is None:

            await context.send("Make sure to pass in arguements")
            await context.invoke(self.bot.get_command("help"),"iam")
            return

        elif author_id in self.userCache:

            await context.send(f'{self.userCache[author_id]["name"]} is already being recorded')
            return

        else:

            # Check if data is stored in DB, and add to cache if it exist:
            projection = {"userstats": 1}
            stored_stats = self.bot.DB.levels.find_one({"_id":context.author.id}, projection)

            if stored_stats is not None and "userstats" in stored_stats:

                # Add to cache:
                self.userCache[author_id] = stored_stats["userstats"]
                await context.send(f'cache has been reset {self.userCache[author_id]["name"]} is being recorded')
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

        await context.send(f'Account for {self.userCache[author_id]["name"]} has been added and now being recorded')

        query = {"_id":context.guild.id}
        toAdd = {"playerAccounts": [self.userCache[author_id]["name"], author_id] }

        # Add user to playerlist in database:
        self.bot.DB.servers.update_one(query, { "$addToSet": toAdd })

        # Push stats to users profile in database aswell:
        self.bot.DB.levels.update_one({"_id":context.author.id}, {"$set": {"userstats": self.userCache[id]} }, upsert=True)


    """
        Calculates caller statistics, from the time the user added there account to the watch list
        or if account has already been recorded from morning PST time.
    """
    @commands.command(help=stats_help)
    async def stats(self, context):

        author_id = str(context.author.id)
        if author_id not in self.userCache:

            # Check if data is stored in DB, and add to cache if it exist:
            projection = {"userstats": 1}
            stored_stats = self.bot.DB.levels.find_one({"_id":context.author.id}, projection)

            if stored_stats is not None and "userstats" in stored_stats:

                # Add to cache:
                self.userCache[author_id] = stored_stats["userstats"]
                await context.send(f'cache has been reset {self.userCache[author_id]["name"]} is being recorded')

            else:

                await context.send(f'User is not being recorded, to begin watching use {context.prefix}iam command')
                await context.invoke(self.bot.get_command("help"),"iam")
                return

        # Processing visual:
        await context.trigger_typing()

        accountID = self.userCache[author_id]["account_id"]
        stats = requests.get(self.api_query_stats.format(accountID, self.WOTB_APP_ID)).json()

        # Calculate overall win ratio:
        new_total_battles = stats["data"][accountID]["statistics"]["all"]["battles"]
        new_wins = stats["data"][accountID]["statistics"]["all"]["wins"]
        overall_wr = "{:.2f}".format((new_wins / new_total_battles)* 100)

        # Calculate daily win ratio:
        old_total_battles = self.userCache[author_id]["total_battles"]
        old_wins = self.userCache[author_id]["wins"]

        daily_wr = 0
        battle_diff = new_total_battles - old_total_battles
        if battle_diff != 0:
            daily_wr = "{:.2f}".format(((new_wins - old_wins) / battle_diff)* 100)

        # Color code embed msg based on win-ratio:
        percent = float(daily_wr)
        color = Color.defualt

        if 50 <= percent < 55:
            color = Color.lightGreen

        elif 55 <= percent < 60:
            color = Color.darkGreen

        elif 60 <= percent < 65:
            color = Color.blue

        elif percent >= 65:
            color = Color.purple

        # Create Embed:
        embed = discord.Embed(
            title = f'{self.userCache[author_id]["name"]} statistics',
            colour = color.value
        )

        embed.set_thumbnail(url=context.author.avatar_url)

        embed.set_footer(text=f'Data cached at {self.userCache[author_id]["datetime"]}')

        embed.add_field(
            name = f'Overall win-ratio: {overall_wr}%',
            value = f'Total battles: {self.userCache[author_id]["total_battles"]:,d} before',
            inline=False
        )

        if percent != 0:

            # recent battle time in los Angeles local time:
            timezone_offset = -7.0
            tzinfo = timezone(timedelta(hours=timezone_offset))

            # Convert from timestamp to local time PST:
            time = datetime.fromtimestamp(stats["data"][accountID]["last_battle_time"],tzinfo)

            embed.add_field(
                name = f'Daily win-ratio: {daily_wr}%',
                value = f'Total battles: {new_total_battles:,d} after\nlast battle time: {time.strftime("%b-%-d %-I:%M %p")}',
                inline=False
            )

        await context.send(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(WorldOfTanks(bot))
