import discord
import logging

from api_token import API_TOKEN
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

client.run(API_TOKEN)
