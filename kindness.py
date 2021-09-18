import discord
import logging
import os
import re
import asyncio

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

# When bot joins a new server it checks if #Welcome and #role-settings channel are created
# if not it creates them. TODO: Ask server Admin for permission to create channels and then delete msg.
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
            break

@client.event
async def on_message(message):

    if message.author == client.user:
        return

    hello_regex = re.compile('^[hH]ello!?|^[hH]i!?|[hH]ey')
    if hello_regex.match(message.content):
        await message.channel.send(greetings())

    await client.process_commands(message) # on_message blocks other commands needs this.

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

# Deletes most recent messages
@client.command(help=dd_help)
async def dd(content, amount = 3):
    def is_user(user):
        return user.id == content.member.id
    await content.channel.purge(limit = amount + 1, check=is_user)

# Mod command that deletes all user messages in a channel.
# TODO: Add permisions so only mod can use and maybe the option to delete another users messages.
@client.command(help=dD_help)
async def DD(content, amount = 3):
    await content.channel.purge(limit = amount + 1)

@client.command()
async def ping(context):
    await context.channel.send(f'ping: {round(client.latency * 1000)}ms')

# Sends a message to roles channel.
# Make adding roles more dynamic, let admin have the ability to create/remove roles.
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
