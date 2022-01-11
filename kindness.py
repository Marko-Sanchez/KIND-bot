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


async def roleEmbed(roles_channel):

    embed = discord.Embed(
        title = 'Server Roles',
        colour = 0xaa6ca3
    )

    embed.set_image(url = client.user.avatar_url)
    for reaction, name in emoji_roles.items():
        embed.add_field(name =reaction, value=name, inline=True)

    # Send embed message
    message = await roles_channel.send(embed=embed)

    # Change to add server specific emotes:
    for reaction in emoji_roles:
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
                    await roleEmbed(created_channel)
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
    author_id = str(message.author.id)
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

        db.levels.update_one(query, {"$inc":{"user_info.exp":5}})

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

# Listens for reaction in #roles channel.
@client.event
async def on_raw_reaction_add(payload):
    if payload.member is None:
        return
    roles_channel = discord.utils.get(payload.member.guild.text_channels, name='roles')

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

    # Payload.member does not exist(in remove), thus different method to get channel.
    guild = client.get_guild(payload.guild_id)
    roles_channel = discord.utils.get(guild.text_channels, name='roles')

    if payload.user_id == client.user.id:
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

# Sends a message to roles channel.
# Make adding roles more dynamic, let admin have the ability to create/remove roles.
@client.command(help=roles_help)
async def roles(context):
    # Get roles channel.
    roles_channel = discord.utils.get(context.guild.text_channels, name='roles')
    if roles_channel is None:
        await context.channel.send('A channel with name \'roles\' is needed', delete_after=30.0)
        return

    await roleEmbed(roles_channel)

# Dynamically add emotes onto role selection on per server base.
@client.command()
async def addRoles(context, emote = None, role_name = None):
    if emote is None or role_name is None:
        return
    # Change this to add to database instead:
    emoji_roles[emote] = role_name

# Dynamically remove emotes from role selection on per server base.
@client.command()
async def removeRoles(context, emote = None, role_name = None):
    if emote is None or role_name is None:
        return

    del emoji_roles[emote]

# Deletes users most recent messages, sleeps to avoid rate limit.
@client.command(help=dd_help)
async def dd(context, amount:int = 3):
    if amount == 0 or amount > 20:
        return
    deleted = 0
    async for message in context.channel.history(limit=50):
        if message.author == context.message.author:
            deleted +=1
            await asyncio.sleep(0.5)
            await message.delete()
        if deleted > amount:
            return

@dd.error
async def dd_error(context, error):
    if isinstance(error, commands.BadArgument):
        await context.send('Make sure to pass in a integer example: !dd 2')

# Administrative command takes in optional arguements
# amount: of messages to delete, member: members message to delete.
@client.command(help=dD_help)
@commands.has_permissions(administrator=True)
async def DD(context, amount: int = 3, member: discord.Member = None):
    if member is None:
        await context.channel.purge(limit = amount + 1)
    else:
        if member is None:
            await context.channel.send(f'User {member} does not exist in this server', delete_after=30.0)
            return

        if amount == 0 or amount > 20:
            return
        deleted = 0
        async for message in context.channel.history(limit=50):
            if member == message.author:
                deleted += 1
                await asyncio.sleep(0.5)
                await message.delete()
            if deleted >= amount:
                return

@DD.error
async def DD_error(context, error):
    if isinstance(error, commands.BadArgument):
        await context.send('Make sure to pass in a integer example: !DD 2 or !DD 4 @USER')
    elif isinstance(error, commands.MissingPermissions):
        # DO nothing for now:
        return

client.run(API_TOKEN)
