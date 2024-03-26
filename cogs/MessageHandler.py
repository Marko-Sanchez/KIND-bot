from functions import *

import random
import re
import discord
from discord.ext import commands

class MessageHandler(commands.Cog):

    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.redisCache = self.bot.redisCache
        self.mongoDB    = self.bot.DB

    RESPONSES = [
        ['hi', 'Hi', 'Hello!', 'hello', 'sup'],
        ['Hey! Welcome',
         'Welcome to the server',
         'Nice to meet you, welcome',
         'Glad you could join us',
         'Nice to have you!',
         'Welcome to the jungle!',
         'Welcome to the party!',
         'ahh mustard']
    ]

    """
        Event listener for user messages, if message contains keywords bot replies to user, then
        gives user experience for chatting.

        @outputs:   If regex matches bot will respond to user with  certain phrases.
                    If user reaches a certain amount of experience points, bot notifys user has
                    leveled up.
    """
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        # If command wait for it to be executed and return:
        elif (await self.bot.get_context(message)).valid:
            await self.bot.process_commands(message)
            return

        random_number = random.randint(1,30)
        if random_number % 3 == 0:

            hello_regex = re.compile('^Hello!?|^Hi!?|Hey|Yo', re.IGNORECASE)
            smh_regex   = re.compile('smh', re.IGNORECASE)

            if hello_regex.match(message.content):
                await message.reply(random.choice(self.RESPONSES[0]))

            elif smh_regex.match(message.content):
                await message.channel.send(f'{message.author.mention} smh my head')

            elif self.bot.user in message.mentions:
                await message.reply(random.choice(self.RESPONSES[1]))

        # Give user experience points for their message:
        guildID = str(message.guild.id) if message.guild is not None else ""
        level   = await self.add_experience(message.author.name, message.author.id, guildID, message.content)
        if level > 0:
            await message.channel.send(f'{message.author.mention} has leveled up to level {level}')


    """
        Gives user experience points for messages sent in guild / server. Pulls users
        information from database and increments points, while also checking if user has
        reached a certain amount of points to level up.

        @params: message{ discord.Message } users mesage from text-channel.

        @behavior: Once points have been added updates database with new information.

        @returns: isNewLevel{ int } if user has leveled up, returns new level.
    """
    async def add_experience(self,authorName: str, authorID: int, guildID: str, message: str):

        authorID_str = str(authorID)
        projection   = {guildID: 1}
        query        = {"_id":authorID, guildID: {"$exists":True} }
        isNewLevel   = 0


        # Get data from cache, else get from database.
        stats = self.redisCache.get_user(authorID_str)
        stats = self.mongoDB.levels.find_one(query, projection) if stats is None else stats

        try:
            if stats is None:
                data     = {guildID: {"user_info": {"exp":5, "level":1} } }
                newField = {"$set": data }

                # add new user or user.newGuild to database:
                self.mongoDB.levels.update_one({"_id":authorID}, newField, upsert=True)

                # add user to cache:
                if self.redisCache.does_user_exist(authorID_str):
                    self.redisCache.set_user(authorID, '$.' + guildID, data.get(guildID))
                else:
                    self.redisCache.set_user(authorID, '$', data, expire=True)

                self.redisCache.log_message(f"Added new user: {authorName}:{authorID} with guild {guildID} to database")
            else:
                if not self.redisCache.does_user_exist(authorID_str):
                    self.redisCache.set_user(authorID, '$', stats, expire=True)

                elif not (self.redisCache.does_guild_exist(authorID_str, guildID)):
                    self.redisCache.set_user(authorID, '$.' + guildID, stats.get(guildID))

                self.redisCache.log_message(f"User: {authorName},{authorID} stats: {stats}")

                words:int = len(message.split())
                exp  :int =  self.redisCache.increment_user(authorID, guildID + ".user_info.exp", words)

                # Calculate new level:
                initial_level = self.redisCache.get_user_field(authorID, guildID + ".user_info.level")
                new_level     = int(exp ** (1/4))

                if initial_level < new_level:
                     isNewLevel = new_level
                     levelPath  = guildID + ".user_info.level"
                     self.redisCache.set_user(authorID, levelPath, new_level)
                     self.mongoDB.levels.update_one(query, {"$inc": {levelPath:1} })

                     self.redisCache.log_message(f"User: {authorName},{authorID} has leveled up to level {new_level}")

                self.mongoDB.levels.update_one({"_id":authorID}, {"$set": {guildID + ".user_info.exp": exp}}, upsert=True)
                self.redisCache.log_message(f"User: {authorName},{authorID} has gained {words} experience points")

        except Exception as e:
            self.redisCache.log_error(e.__str__())

        return isNewLevel



async def setup(bot: commands.Bot):
    await bot.add_cog(MessageHandler(bot))
