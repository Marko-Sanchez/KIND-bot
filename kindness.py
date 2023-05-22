import discord
import logging
import os
import re
import asyncio
import pymongo

from functions import *
from discord.ext import commands

API_TOKEN = os.environ.get('API_TOKEN')
MONGO_TOKEN = os.environ.get('MONGO_TOKEN')

db = pymongo.MongoClient(MONGO_TOKEN).discord

"""
    Grabs servers custom prefix from either the local cache or database.
    If prefix is not cached it will query the database and cache it. Cache
    is reset after a certain amount of calls to it.

    @params: _ { bot object } defualt value that needs to be passed in, contains info on bot / client.
            message { discord.Message } object containing command call.
"""
async def getPrefix(_, message):

    # Message from DM's:
    if message.guild == None:
        return '!'

    guildID = message.guild.id
    strID = str(guildID)

    # Check if server prefix is in cache:
    if prefixExist(strID):
        return grabPrefix(strID)

    server_settings = db.servers.find_one({"_id": guildID})

    # If guild exist in database cache prefix, else create field with default prefix and cache:
    if server_settings is not None and "CommandPrefix" in server_settings:

        # Update Cache prefix:
        addPrefix(strID, server_settings["CommandPrefix"])
        return server_settings["CommandPrefix"]

    else:

        newField = {"$set": {"_id":guildID,"CommandPrefix":'!'}}
        db.servers.update_one({"_id": guildID}, newField, upsert=True)

        # add prefix to cache:
        addPrefix(strID, '!')
        return '!'

# Output logging to termial / stdout:
logging.basicConfig(level=logging.INFO)

# Set default bot actions, remove help command for custom made one:
client = commands.Bot(command_prefix = getPrefix, help_command=None, intents = discord.Intents.all())
client.remove_command('help')

# Database connection for usage in cogs:
client.DB = db

# Load all cogs:
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('py'):
            await client.load_extension(f'cogs.{filename[:-3]}')


"""
    Creates an embed message, with reactions associated with roles,
    then sends to #roles channel. Querys database for role names and emotes.

    @params: guildID { int } guild ID of server to send embed.
            roles_channel {discord.TextChannel} channel where embed will be sent.

    @returns: A discord embed message with emote reactions associated with roles.
"""
async def roleEmbed(_guildID, roleChannel):

    embed = discord.Embed(
        title = 'Server Roles',
        colour = 0xaa6ca3
    )

    # Query emoji-role list:
    emoji_rolez =  db.servers.find_one({"_id":_guildID}, {"emojis": 1})

    # No roles currently in server:
    if emoji_rolez is None or "emojis" not in emoji_rolez:
        await roleChannel.send("No roles curently in server, to add roles use addRoles:")
        return

    embed.set_image(url = client.user.avatar.url)

    for reaction, name in emoji_rolez["emojis"].items():
        embed.add_field(name =reaction, value=name, inline=True)

    # Send embed message
    message = await roleChannel.send(embed=embed)

    invalidEmojis = {}      # will hold invalid emojis to notify admin.

    # Iterate through roles list and add there associated emote:
    for reaction, name in emoji_rolez["emojis"].items():

        try:
            await message.add_reaction(reaction)

        except discord.errors.HTTPException:

            invalidEmojis[reaction] = name

    # If user passed in invalid emojis, alert them:
    if len(invalidEmojis) != 0:
        msg = ""

        for key, name in invalidEmojis.items():
            msg += f'{key} is an invalid emoji make sure to remove it using, removeRoles command\n'

        await roleChannel.send(msg)


"""
    When joining a new server admin will recieve a message prompting them to give the bot
    permission to create both '#welcome' and '#roles' channel if they do not already exist.
    If permission is granted creates channels, else dosen't.

    @params: guild {discord.Guild} object containing information of guild joined.

    @returns: Two embed messages for each channel whether they should be created or not.
"""
@client.event
async def on_guild_join(guild):

    guildAdmin = guild.owner
    ask_welcome = ask_roleSetting = False# whether to create specific channels:
    total_request = 0                    # number of channels to create:

    reactions = ["\u2705", "\u274C"]     # Green check and red X emotes:

    # If channels exist set their bools:

    channel = discord.utils.get(guild.text_channels, name='welcome')
    if channel is None:
        ask_welcome = True

    channel = discord.utils.get(guild.text_channels, name='roles')
    if channel is None:
        ask_roleSetting = True

    # All channels present:
    if not ask_welcome and not ask_roleSetting:
        return

    # Send embed message to server admin asking for permission to create text channels.

    if ask_welcome:

        embed = discord.Embed(
            title = 'Channel Creation',
            colour = 0xaa6ca3
        )

        embed.add_field(name ='#welcome', value='Create Welcome channel', inline=True)
        admin_message = await guildAdmin.send(embed=embed)

        for emoji in reactions:
            await admin_message.add_reaction(emoji)

        total_request += 1

    if ask_roleSetting:

        embed = discord.Embed(
            title = 'Channel Creation',
            colour = 0xaa6ca3
        )

        embed.add_field(name ='#roles', value='Create Role channel', inline=True)
        admin_message = await guildAdmin.send(embed=embed)

        for emoji in reactions:
            await admin_message.add_reaction(emoji)

        total_request += 1

    def check(reaction, user):
        return str(reaction.emoji) in reactions and user.id == guildAdmin.id

    # Wait for user to react to one of the messages:
    for _ in range(total_request):

        try:

            # reaction chosen and admin object:
            reaction, guildAdmin = await client.wait_for('reaction_add', check= check, timeout = 120.0)
            channelName = reaction.message.embeds[0].fields[0].name

            # If admin chose to create channel create it, else notify them channel wasn't created:
            if str(reaction.emoji) == reactions[0]:
                created_channel = await guild.create_text_channel(channelName.strip('#'))

                await created_channel.set_permissions(guild.default_role, read_messages = True,
                                                                    add_reactions = False,
                                                                    send_messages = True,
                                                                    manage_emojis = False,
                                                                    manage_messages = False,
                                                                    mention_everyone=False,
                                                                    read_message_history=True,
                                                                    attach_files=False)

                # If we are creating 'roles' channel, send roles embed message to newly created channel:
                if channelName.strip('#') == 'roles':
                    await roleEmbed(guild.id, created_channel)

            else:
                await guildAdmin.send(f'{channelName} was not created')

            # clean up and delete already proccesed message:
            await reaction.message.delete()

        # Admin did not react within the allocated time:
        except asyncio.TimeoutError:
            break

    await guildAdmin.send("For a list of commands type `!help` in server")

"""
    Event listener for user messages, if message contains keywords bot replies to user, then
    gives user experience for chatting.

    @outputs:   If regex matches bot will respond to user with  certain phrases.
                If user reaches a certain amount of experience points, bot notifys user has
                leveled up.
"""
@client.event
async def on_message(message):

    if message.author.bot:
        return

    # If command wait for it to be executed and return:
    elif (await client.get_context(message)).valid:
        await client.process_commands(message)
        return

    if random.randint(1,10) % 3 == 0:

        # Regex patterns to match, for bot response:
        hello_regex = re.compile('^[hH]ello!?|^[hH]i!?|[hH]ey')
        smh_regex = re.compile('smh')

        # string contains greeting:
        if hello_regex.match(message.content):
            await message.reply(greetings())

        # string contains 'smh':
        elif smh_regex.match(message.content):
            await message.channel.send(f'{message.author.mention} smh my head')

        # User mentions bot:
        elif client.user in message.mentions:
            await message.reply(reply())

    # Give user expereince points for their message:
    await add_experience(message)

"""
    Gives user expereince points for messages sent in guild / server. Pulls users
    information from database and increments points, while also checking if user has
    reached a certain amount of points to level up.

    @params: message{ discord.Message } users mesage from text-channel.

    @returns: Once points have been added updates database with new information.
              If user has reached a certain amount of points sends message to channel
              notifying them.
"""
@client.event
async def add_experience(message):

    authorID = message.author.id
    guildID = str(message.author.guild.id)

    # Query user information and only send back information for this guild:
    query = {"_id":authorID, guildID: {"$exists":True} }
    projection = {guildID: 1}

    stats = db.levels.find_one(query, projection)

    # If user does not exist or guild is not in user account:
    if stats is None or guildID not in stats:

        newField = {"$set": { guildID: {"user_info": {"exp":5, "level":1} } } }
        db.levels.update_one({"_id":authorID}, newField, upsert= True)

    else:

        # Increment points to pre-existing expereince pool:
        exp = stats[guildID]["user_info"]["exp"] + 5

        initial_level = stats[guildID]["user_info"]["level"]
        new_level = int(exp ** (1/4))

        # Increment points in database:
        expPath = guildID + ".user_info.exp"
        db.levels.update_one(query, {"$inc": {expPath:5} })

        # Notify user they have leveled up:
        if initial_level < new_level:

             await message.channel.send(f'{message.author} has leveled up to level {new_level}')

             levelPath = guildID + ".user_info.level"
             db.levels.update_one(query, {"$inc":{levelPath:1}})

"""
    Event listener for emote reaction additions, if user reacted in '#roles' channel
    the bot will give them the associated role of that emote. Querys database for
    servers emote list.

    @params: payload { discord.RawReactionActionEvent } information on reaction event.

    @outputs: If emote is associated with a valid role, grants user role permission. Else
              outputs error / warning message.
"""
@client.event
async def on_raw_reaction_add(payload):

    # Reaction happened in guild not DM's:
    if payload.member is None:
        return

    # Grab channel where roles embed message is:
    rolesChannel = discord.utils.get(payload.member.guild.text_channels, name='roles')

    # If bot adds a reaction ignore.
    if payload.member.bot:
        return

    # Roles channel does not exist:
    elif rolesChannel is None:
        return

    # If we are not in roles channel ignore.
    elif payload.channel_id != rolesChannel.id:
        return

    else:

        # Grab role list from database and check whether field exist:
        emoji_rolez =  db.servers.find_one({"_id":payload.guild_id}, {"emojis": 1})

        if emoji_rolez is None or "emojis" not in emoji_rolez:
            return

        guild = client.get_guild(payload.guild_id)

        if guild is None:
            return

        try:

            role = discord.utils.get(guild.roles, name=emoji_rolez["emojis"][str(payload.emoji)])

            if role is None:
                await rolesChannel.send(f'`A Role has not been set for` {payload.emoji}` {emoji_rolez["emojis"][str(payload.emoji)]}, Notify admin`', delete_after = 30.0)
                return

            await payload.member.add_roles(role)

        except discord.errors.Forbidden:

            await guild.owner.send(reaction_permission(emoji_rolez["emojis"][str(payload.emoji)]), delete_after = 60)

"""
    Event listener for removing emote reactions, if user removes a reaction from the
    'roles' channel the emotes associated role get removed from the user.

    @params: payload { discord.RawReactionActionEvent } object containing information on reaction.

    @outputs: Removes role associated with reaction.
"""
@client.event
async def on_raw_reaction_remove(payload):

    guild = client.get_guild(payload.guild_id)

    if guild is None:
        return

    # Grab channel where roles embed message is:
    rolesChannel = discord.utils.get(guild.text_channels, name='roles')

    # If bot removes a reaction ignore.
    if payload.user_id == client.user.id:
        return

    # If we are not in roles channel ignore.
    elif rolesChannel is None or payload.channel_id != rolesChannel.id:
        return

    else:

        # Grab role from database and check whether field exist:
        emoji_rolez =  db.servers.find_one({"_id":payload.guild_id})

        if emoji_rolez is None or "emojis" not in emoji_rolez:
            return

        try:

            role = discord.utils.get(guild.roles, name=emoji_rolez["emojis"][str(payload.emoji)])
            if role is None:
                return

            user = guild.get_member(payload.user_id)

            await user.remove_roles(role)

        except discord.errors.Forbidden:

            await guild.owner.send(reaction_permission(emoji_rolez["emojis"][str(payload.emoji)]), delete_after = 60)

"""
    Creates and sends an embed message to '#roles' channel containg role names
    and emote reactions.

    @output: Embed message with reaction to obtain roles.
"""
@commands.has_permissions(manage_roles=True)
@client.command(help=roles_help)
async def roles(context):

    rolesChannel = discord.utils.get(context.guild.text_channels, name='roles')

    if rolesChannel is None:
        await context.channel.send('A channel with name \'roles\' is needed')
        return

    await roleEmbed(context.guild.id, rolesChannel)

"""
    Adds emote-role pair to database to be used in embed message for role selection.

    @params: emote { discord.Emoji } emote to associate role with.
             role_name { string } server role to give to user.
"""
@commands.has_permissions(manage_roles=True)
@client.command(help=addRolesH)
async def addRoles(context, emote = None, role_name = None):

    if emote is None or role_name is None:
        await context.invoke(client.get_command("help"),"addRoles")
        return

    # Query Database:
    emoji_rolez = db.servers.find_one({"_id":context.guild.id}, {"emojis": 1})

    # If server or "emojis" field not in database, create it:
    if emoji_rolez is None or "emojis" not in emoji_rolez:

        emoji_rolez = {"CommnadPrefix":context.prefix, "emojis": {emote:role_name} }
        db.servers.update_one({"_id":context.guild.id}, {"$set": emoji_rolez}, upsert=True)

    else:

        field = "emojis." + emote
        db.servers.update_one({"_id":context.guild.id}, {"$set": {field:role_name} })

    await context.channel.send(f'Added {emote} with role {role_name}')

@addRoles.error
async def addRoles_error(context, error):

    if isinstance(error, commands.MissingPermissions):
        await context.send("Sorry you don't have permission to use this command, ask your administrator")

"""
    Given an emote, removes associated role. Querys database for emote and removes value.

    @params: emote { discord.Emoji } emote associated with role to be removed.

    @outputs: removes emote from appearing in embed message in 'roles' channel.
"""
@commands.has_permissions(manage_roles=True)
@client.command(help=removeRolesH)
async def removeRoles(context, emote = None):

    if emote is None:
        await context.invoke(client.get_command("help"),"removeRoles")
        return

    emoji_rolez = db.servers.find_one({"_id":context.guild.id}, {"emojis": 1})

    if emoji_rolez is None or "emojis" not in emoji_rolez:

        await context.channel.send(f'No registered emote-roles found, to add roles use')
        await context.invoke(client.get_command("help"),"addRoles")
        return

    else:

        field = "emojis." + emote
        result = db.servers.update_one({"_id":context.guild.id}, {"$unset": {field:""} })

        if result.modified_count == 0:
            await context.send("That emoji does not exst in the list of emote-role values")

        else:
            await context.send(f'Removed {emoji_rolez["emojis"][emote]} role')

"""
    Outputs a list of the servers emote-role relationships.
"""
@commands.has_permissions(manage_roles=True)
@client.command(help=listRolesH)
async def listRoles(context):

    emoji_rolez = db.servers.find_one({"_id":context.guild.id}, {"emojis": 1})

    # Server not in database or emojis field doesn't exist:
    if emoji_rolez is None or "emojis" not in emoji_rolez or len(emoji_rolez["emojis"]) == 0:

        await context.channel.send(f'Roles list is empty, to add roles use {context.prefix}addRoles')
        await context.invoke(client.get_command("help"),"addRoles")
        return

    for x, y in emoji_rolez["emojis"].items():
        await context.send(f'{x} with {y}')

"""
    Change server prefix to desired character for guild / server. Adds
    prefix to cache and database.
"""
@commands.has_permissions(administrator=True)
@client.command(help="Set custom command prefix for server")
async def setPrefix(context, prefix = None):

    if prefix is None:
        await context.invoke(client.get_command("help"),"setPrefix")
        return

    elif len(prefix) > 1 or prefix.isalpha() or prefix.isdigit():
        await context.channel.send(f'Prefix must be one character long and not a-z,A-Z,0-9')
        return

    server_settings = db.servers.find_one({"_id":context.guild.id})

    if server_settings is not None:

        db.servers.update_one({"_id":context.guild.id}, {"$set": {"CommandPrefix":prefix}}, upsert=True)
        await context.channel.send(f'Prefix Updated to {prefix}')

    # Add prefix to Cache:
    addPrefix(str(context.guild.id), prefix)

@client.command(help="Sync commands")
@commands.guild_only()
@commands.is_owner()
async def sync(context):
    await context.bot.tree.sync()
    # for guild in client.guilds:
    #     try:
    #         await client.tree.sync(guild=guild)
    #         await context.channel.send(f'Synced {guild.name}')
    #     except:
            # pass

async def main():
    async with client:
        await load_cogs()
        await client.start(API_TOKEN)

asyncio.run(main())
