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

    hello_regex = re.compile('^[hH]ello!?|^[hH]i!?')
    if hello_regex.match(message.content): # was using message.content.startswith('hello') before
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

# Delete Most recent messages
# TODO: user permission, and only delete user's messages.
@client.command()
async def dd(content, amount = 3):
    await content.channel.purge(limit = amount + 1)

@client.command()
async def ping(context):
    await context.channel.send(f'ping: {round(client.latency * 1000)}ms')

# -- Make this better --
API_TOKEN = ''
if (exists('./.env')):
    env_path = '.env'
    load_dotenv(dotenv_path=env_path)
    API_TOKEN = os.environ.get('API_TOKEN')
else:
    API_TOKEN = os.environ.get('API_TOKEN')

client.run(API_TOKEN)
