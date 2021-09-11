import discord
import logging
import os

from os.path import exists
from dotenv import load_dotenv
from functions import *

logging.basicConfig(level=logging.INFO)
client = discord.Client()

@client.event
async def on_ready():
    print('online')

@client.event
async def on_message(message):
    # If we are the one's messaging, ignore: avoids infinite loops.
    if message.author == client.user:
        return

    if message.content.startswith('hello'):
        await message.channel.send(greetings())

# -- Make this better --
API_TOKEN = ''
if (exists('./.env')):
    env_path = '.env'
    load_dotenv(dotenv_path=env_path)
    API_TOKEN = os.environ.get('API_TOKEN')
else: 
    API_TOKEN = os.environ.get('API_TOKEN')

client.run(API_TOKEN)
