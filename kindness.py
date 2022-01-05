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
# # -- Make this better --
# API_TOKEN = ''
# MONGO_TOKEN = ''
# if (exists('./.env')):
#     env_path = '.env'
#     load_dotenv(dotenv_path=env_path)
#     API_TOKEN = os.environ.get('API_TOKEN')
#     MONGO_TOKEN = os.environ.get('MONGO_TOKEN')
# else:
#     API_TOKEN = os.environ.get('API_TOKEN')
#     MONGO_TOKEN = os.environ.get('MONGO_TOKEN')

cluster = pymongo.MongoClient(MONGO_TOKEN)
db = cluster.discord

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
discord.member = True
client = commands.Bot(command_prefix = '!', intents = intents)

# When bot joins a new server it checks if #Welcome and #role-settings channel are created
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

    channel = discord.utils.get(guild.text_channels, name='role-setting')
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
        embed.add_field(name ='#role-setting', value='Create Role-setting channel', inline=True)
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
            channel = reaction.message.embeds[0].fields[0].name

            # Create channel otherwise ignore.
            if str(reaction.emoji) == reactions[0]:
                print(f'{str(reaction.emoji)} {channel}')
                created_channel = await guild.create_text_channel(channel.strip('#'))
                await created_channel.set_permissions(guild.default_role, read_messages = True,
                                                                    add_reactions = False,
                                                                    send_messages = False,
                                                                    manage_emojis = False,
                                                                    manage_messages = False,
                                                                    mention_everyone=False,
                                                                    read_message_history=True,
                                                                    attach_files=False)
            else:
                print(f'Admin declined to add {channel}')
            await reaction.message.delete()
        except asyncio.TimeoutError:
            print('Admin declined to React')
            await reaction.message.delete()
            break

@client.event
async def on_message(message):

    if message.author == client.user:
        return
    elif (await client.get_context(message)).valid:
        await client.process_commands(message) # Wait for command to be executed.
        return

    hello_regex = re.compile('^[hH]ello!?|^[hH]i!?|[hH]ey')
    if hello_regex.match(message.content):
        await message.channel.send(greetings())

    # User level up:
    await add_experience(message)

@client.event
async def add_experience(message):
    author_id = str(message.author.id)# Convert to string to avoid duplicates
    g_id = message.author.guild.name
    query = {g_id:author_id}

    stats = db.levels.find_one(query)
    if stats is None:
        newuser = {g_id:author_id,"user_info":{"exp":5,"level":1}}
        db.levels.insert_one(newuser)
    else:
        exp = stats["user_info"]["exp"] + 5
        initial_level = stats["user_info"]["level"]
        new_level = int(exp ** (1/4))

        db.levels.update_one(query, {"$set":{"user_info.exp":exp}})

        if initial_level < new_level:
             await message.channel.send(f'{message.author} has leveled up to level {new_level}')
             db.levels.update_one(query, {"$set":{"user_info.level":new_level}})

@client.event
async def on_member_join(member):

    channel = discord.utils.get(member.guild.text_channels, name='welcome')
    if channel is None:
        return

    await channel.send(f'{member} {welcome()}')

@client.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name='welcome')

    if member == client.user:
        return
    elif channel is None:
        return
    # Instead of saying a goodbye message maybe delete there welcome from the welcome channel
    await channel.send(f'{member} imagine leaving lmao, bye <:nail_care:886811404626165861>')

# Listens for reaction in #role-setting channel.
@client.event
async def on_raw_reaction_add(payload):
    roles_channel = discord.utils.get(payload.member.guild.text_channels, name='role-setting')

    if payload.member == client.user:
        # If bot removes a reaction ignore.
        return
    elif roles_channel is None:
        return
    elif payload.channel_id != roles_channel.id:
        # If we are not in roles channel ignore.
        return
    elif str(payload.emoji) in emoji_roles:
        try:
            # Add role to user
            guild = client.get_guild(payload.guild_id)
            role = discord.utils.get(guild.roles, name=emoji_roles[str(payload.emoji)])
            await payload.member.add_roles(role)
        except discord.errors.Forbidden:
            # Let admin know to set role higher.
            admin = guild.owner
            await admin.send(reaction_permission(emoji_roles[str(payload.emoji)]), delete_after = 60)

@client.event
async def on_raw_reaction_remove(payload):
    guild = client.get_guild(payload.guild_id)
    roles_channel = discord.utils.get(guild.text_channels, name='role-setting')

    if payload.member == client.user:
        # If bot removes a reaction ignore.
        return
    elif payload.channel_id != roles_channel.id:
        # If we are not in roles channel ignore.
        return
    elif str(payload.emoji) in emoji_roles:
        try:
            # Remove role from user
            role = discord.utils.get(guild.roles, name=emoji_roles[str(payload.emoji)])
            user = guild.get_member(payload.user_id)
            await user.remove_roles(role)
        except discord.errors.Forbidden:
            # Let admin know to set role higher.
            admin = guild.owner
            await admin.send(reaction_permission(emoji_roles[str(payload.emoji)]), delete_after = 60)

# Deletes users most recent messages, sleeps to avoid rate limit.
@client.command(help=dd_help)
async def dd(context, amount = 3):

    if amount == 0: return
    deleted = 0
    async for message in context.channel.history(limit=50):
        if message.author == context.message.author:
            deleted +=1
            await asyncio.sleep(0.5)
            await message.delete()
        if deleted > amount:
            return

# Mod command that deletes all user messages in a channel.
# TODO: Option to delete another users messages.
@client.command(help=dD_help)
@commands.has_permissions(administrator=True)
async def DD(context, amount = 3):
    await context.channel.purge(limit = amount + 1)

@client.command()
async def ping(context):
    await context.channel.send(f'ping: {round(client.latency * 1000)}ms')

# Sends a message to roles channel.
# Make adding roles more dynamic, let admin have the ability to create/remove roles.
@client.command(help=roles_help)
async def roles(context):
    # Get roles channel.
    roles_channel = discord.utils.get(context.guild.text_channels, name='role-setting')
    embed = discord.Embed(
        title = 'Server Roles',
        colour = 0xaa6ca3
    )

    embed.set_image( url = client.user.avatar_url)
    # embed.set_thumbnail( url = client.user.avatar_url) # Use this to use server avatar
    for reaction, name in emoji_roles.items():
        embed.add_field(name =reaction, value=name, inline=True)

    # Send embed message
    message = await roles_channel.send(embed=embed)
    for reaction in emoji_roles:
        await message.add_reaction(reaction)# Gamer

client.run(API_TOKEN)
