import discord
from api_token import API_TOKEN

client = discord.Client()

@client.event
async def on_ready():
    print('online')

@client.event
async def on_message(message):
    # If we are the one's messaging, ignore: avoids infinite loops.
    if message.author == client.user:
        return

    if message.content == 'hello':
        await message.channel.send('Hi there')

client.run(API_TOKEN)
