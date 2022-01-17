import discord
import logging
import os
import re
import asyncio

from discord.ext import commands
from os.path import exists
from dotenv import load_dotenv
from functions import *
import pymongo
from pymongo import MongoClient

API_TOKEN = os.environ.get('API_TOKEN')
MONGO_TOKEN = os.environ.get('MONGO_TOKEN')

cluster = pymongo.MongoClient(MONGO_TOKEN)
db = cluster.discord

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
discord.member = True
client = commands.Bot(command_prefix = '!', help_command=None, intents = intents)
client.remove_command('help')

# Load Cogs:
for filename in os.listdir('./cogs'):
    if filename.endswith('py'):
        client.load_extension(f'cogs.{filename[:-3]}')


async def roleEmbed(_guildID, roles_channel):

    embed = discord.Embed(
        title = 'Server Roles',
        colour = 0xaa6ca3
    )

    # Grab role from database:
    query = {"_id":_guildID}
    emoji_rolez =  db.servers.find_one(query)

    embed.set_image(url = client.user.avatar_url)
    for reaction, name in emoji_rolez["emojis"].items():
        embed.add_field(name =reaction, value=name, inline=True)

    # Send embed message
    message = await roles_channel.send(embed=embed)

    # Change to add server specific emotes:
    for reaction, name in emoji_rolez["emojis"].items():
        await message.add_reaction(reaction)


# When bot joins a new server it checks if #Welcome and #roles channels are created
# if not it creates them.
@client.event
async def on_guild_join(guild):
    admin = guild.owner
    ask_welcome = ask_roleSetting = False
    total_request = 0
    reactions = ["\u2705", "\u274C"]

    channel = discord.utils.get(guild.text_channels, name='welcome')
    if channel is None:
        ask_welcome = True

    channel = discord.utils.get(guild.text_channels, name='roles')
    if channel is None:
        ask_roleSetting = True

    # All channels present.
    if not ask_welcome and not ask_roleSetting:
        return

    # Send embed message to server admin asking for permission to create text channels.
    if ask_welcome:
        embed = discord.Embed(
            title = 'Channel Creation',
            colour = 0xaa6ca3
        )
        embed.add_field(name ='#welcome', value='Create Welcome channel', inline=True)
        admin_message = await admin.send(embed=embed)
        for emoji in reactions:
            await admin_message.add_reaction(emoji)
        total_request += 1

    if ask_roleSetting:
        embed = discord.Embed(
            title = 'Channel Creation',
            colour = 0xaa6ca3
        )
        embed.add_field(name ='#roles', value='Create Role channel', inline=True)
        admin_message = await admin.send(embed=embed)
        for emoji in reactions:
            await admin_message.add_reaction(emoji)
        total_request += 1

    def check(reaction, user):
        return str(reaction.emoji) in reactions and user.id == admin.id
    # Wait for user
    for request in range(total_request):
        try:
            reaction, user = await client.wait_for('reaction_add', check=check, timeout= 60.0)
            channelName = reaction.message.embeds[0].fields[0].name

            # Create channel otherwise ignore.
            if str(reaction.emoji) == reactions[0]:
                created_channel = await guild.create_text_channel(channelName.strip('#'))
                await created_channel.set_permissions(guild.default_role, read_messages = True,
                                                                    add_reactions = False,
                                                                    send_messages = False,
                                                                    manage_emojis = False,
                                                                    manage_messages = False,
                                                                    mention_everyone=False,
                                                                    read_message_history=True,
                                                                    attach_files=False)
                # If we are creating 'roles' channel, send roles embed:
                if channelName.strip('#') == 'roles':
                    await roleEmbed(guild.id, created_channel)
            else:
                print(f'Admin declined to add {channelName}')
            await reaction.message.delete()
        except asyncio.TimeoutError:
            print('Admin declined to React')
            await reaction.message.delete()
            break

@client.event
async def on_message(message):

    if message.author.bot:
        return
    elif (await client.get_context(message)).valid:
        await client.process_commands(message) # Wait for command to be executed.
        return

    hello_regex = re.compile('^[hH]ello!?|^[hH]i!?|[hH]ey')
    if hello_regex.match(message.content):
        await message.channel.send(greetings())
    elif client.user in message.mentions:
        await message.channel.send(reply())

   # User level up:
    await add_experience(message)

@client.event
async def add_experience(message):
    author_id = message.author.id
    g_id = str(message.author.guild.id)
    query = {"_id":author_id, g_id: {"$exists":True}}
    projection = {g_id: 1}

    stats = db.levels.find_one(query, projection)
    if stats is None:
        newField = {"$set": {g_id:{"user_info":{"exp":5, "level":1}}}}
        db.levels.update_one({"_id":author_id}, newField, upsert= True)
    else:
        exp = stats[g_id]["user_info"]["exp"] + 5
        initial_level = stats[g_id]["user_info"]["level"]
        new_level = int(exp ** (1/4))

        expPath = g_id + ".user_info.exp"
        db.levels.update_one(query, {"$inc":{expPath:5}})

        if initial_level < new_level:
             await message.channel.send(f'{message.author} has leveled up to level {new_level}')
             levelPath = g_id + ".user_info.level"
             db.levels.update_one(query, {"$inc":{levelPath:1}})

# Listens for reaction in #roles channel.
@client.event
async def on_raw_reaction_add(payload):
    if payload.member is None:
        return
    roles_channel = discord.utils.get(payload.member.guild.text_channels, name='roles')

    if payload.member.bot:
        # If bot adds a reaction ignore.
        return
    elif roles_channel is None:
        return
    elif payload.channel_id != roles_channel.id:
        # If we are not in roles channel ignore.
        return
    else:
        try:
            # Grab role from database:
            query = {"_id":payload.guild_id}
            emoji_rolez =  db.servers.find_one(query)

            # Add role to user
            guild = client.get_guild(payload.guild_id)
            role = discord.utils.get(guild.roles, name=emoji_rolez["emojis"][str(payload.emoji)])

            if role is None:
                await roles_channel.send(f'`A Role has not been set for` {payload.emoji}` {emoji_rolez["emojis"][str(payload.emoji)]}, Notify admin`', delete_after = 30.0)
                return
            await payload.member.add_roles(role)
        except discord.errors.Forbidden:
            # Let admin know to set role higher.
            admin = guild.owner
            await admin.send(reaction_permission(emoji_rolez["emojis"][str(payload.emoji)]), delete_after = 60)

@client.event
async def on_raw_reaction_remove(payload):

    # Payload.member does not exist(in remove), thus different method to get channel.
    guild = client.get_guild(payload.guild_id)
    roles_channel = discord.utils.get(guild.text_channels, name='roles')

    if payload.user_id == client.user.id:
        # If bot removes a reaction ignore.
        return
    elif payload.channel_id != roles_channel.id:
        # If we are not in roles channel ignore.
        return
    else:
        try:

            # Grab role from database:
            query = {"_id":payload.guild_id}
            emoji_rolez =  db.servers.find_one(query)

            # Remove role from user
            role = discord.utils.get(guild.roles, name=emoji_rolez["emojis"][str(payload.emoji)])
            if role is None:
                return

            user = guild.get_member(payload.user_id)
            await user.remove_roles(role)
        except discord.errors.Forbidden:
            # Let admin know to set role higher.
            admin = guild.owner
            await admin.send(reaction_permission(emoji_rolez["emojis"][str(payload.emoji)]), delete_after = 60)

# Sends a embed message to roles channel, with user roles:
@client.command(help=roles_help)
async def roles(context):
    # Get roles channel.
    roles_channel = discord.utils.get(context.guild.text_channels, name='roles')
    if roles_channel is None:
        await context.channel.send('A channel with name \'roles\' is needed', delete_after=30.0)
        return

    await roleEmbed(context.guild.id, roles_channel)

# Dynamically add emotes onto role selection on per server base:
@client.command(help=addRolesH)
async def addRoles(context, emote = None, role_name = None):
    if emote is None or role_name is None:
        return

    query = {"_id":context.guild.id}
    emoji_rolez = db.servers.find_one(query)
    if emoji_rolez is None:
        emoji_rolez = {"_id":context.guild.id, "emojis":{emote:role_name}}
        db.servers.insert_one(emoji_rolez)
    else:
        field = "emojis." + emote
        db.servers.update_one(query, {"$set":{field:role_name}})

# Dynamically remove emotes from role selection on per server base.
@client.command(help=removeRolesH)
async def removeRoles(context, emote = None):
    if emote is None:
        return

    query = {"_id":context.guild.id}
    emoji_rolez = db.servers.find_one(query)
    if emoji_rolez is None:
        #User has not added roles to server:
            return
    else:
        field = "emojis." + emote
        db.servers.update_one(query, {"$unset":{field:""}})

# List all the roles for the current server:
@client.command(help=listRolesH)
async def listRoles(context):
    query = {"_id":context.guild.id}

    emoji_rolez = db.servers.find_one(query)
    for x, y in emoji_rolez["emojis"].items():
        await context.send(f'{x} and {y}')

client.run(API_TOKEN)
