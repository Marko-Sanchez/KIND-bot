import discord
import logging
import os
import re

from discord.ext import commands
from os.path import exists
from dotenv import load_dotenv
from functions import *

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
discord.member = True
client = commands.Bot(command_prefix = '!', intents = intents)

@client.event
async def on_ready():
    print('online')

@client.event
async def on_message(message):
    # If we are the one's messaging, ignore: avoids infinite loops.
    if message.author == client.user:
        return

    hello_regex = re.compile('^[hH]ello!?|^[hH]i!|[hH]ey?')
    if hello_regex.match(message.content):
        await message.channel.send(greetings())

    await client.process_commands(message) # on_message blocks other commands needs this.

@client.event
async def on_member_join(member):
    channel = client.get_channel(886433874664628264) # update this to be more dynamic
    await channel.send(f'{member} {welcome()}')

@client.event
async def on_member_remove(member):
    channel = client.get_channel(886433874664628264)
    await channel.send(f'{member} imagine leaving lmao, bye <:nail_care:886811404626165861>')

# Goal is to add a role to user, thereby granting them with a gamer tag to let use know
# How active they plan to be. Toggle to turn off tag also.
@client.event
async def on_raw_reaction_add(payload):
    roles_channel = 887087596457558037

    if payload.member == client.user:
        # If bot removes a reaction ignore.
        return
    elif payload.channel_id != roles_channel:
        # If we are not in roles channel ignore.
        return
    elif str(payload.emoji) in emoji_roles:
        # Add role to user
        guild = client.get_guild(payload.guild_id)
        role = discord.utils.get(guild.roles, name=emoji_roles[str(payload.emoji)])
        await payload.member.add_roles(role)

@client.event
async def on_raw_reaction_remove(payload):
    roles_channel = 887087596457558037

    if payload.member == client.user:
        # If bot removes a reaction ignore.
        return
    elif payload.channel_id != roles_channel:
        # If we are not in roles channel ignore.
        return
    elif str(payload.emoji) in emoji_roles:
        # Remove role from user
        guild = client.get_guild(payload.guild_id)
        role = discord.utils.get(guild.roles, name=emoji_roles[str(payload.emoji)])
        user = guild.get_member(payload.user_id)
        await user.remove_roles(role)

# Delete Most recent messages
# TODO: user permission, and only delete user's messages.
@client.command()
async def dd(content, amount = 3):
    await content.channel.purge(limit = amount + 1)

@client.command()
async def ping(context):
    await context.channel.send(f'ping: {round(client.latency * 1000)}ms')

# Sends a message to roles channel.
@client.command()
async def embedM(context):
    # Get roles channel.
    channel = client.get_channel(887087596457558037)
    embed = discord.Embed(
        title = 'Server Roles',
        colour = 0xaa6ca3
    )

    embed.set_image( url = client.user.avatar_url)
    # embed.set_thumbnail( url = client.user.avatar_url) # Use this to use server avatar
    embed.add_field(name ='<:military_medal:887088761110929439>', value='Gamer', inline=True)
    embed.add_field(name ='<:books:887536109175853137>', value='Student', inline=True)
    embed.add_field(name ='<:trophy:887535212693696572>', value='Tournament', inline=True)

    # Send embed message
    message = await channel.send(embed=embed)
    await message.add_reaction("\U0001F396")# Gamer
    await message.add_reaction("\U0001F4DA")# Student
    await message.add_reaction("\U0001F3C6")# Tournament


# -- Make this better --
API_TOKEN = ''
if (exists('./.env')):
    env_path = '.env'
    load_dotenv(dotenv_path=env_path)
    API_TOKEN = os.environ.get('API_TOKEN')
else:
    API_TOKEN = os.environ.get('API_TOKEN')

client.run(API_TOKEN)
