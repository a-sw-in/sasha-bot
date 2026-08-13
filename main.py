import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'hey all, I am {bot.user.name} and I am online now!')

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel:
        await channel.send(f'Welcome to the server, {member.mention}!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "shit" in message.content.lower():
        await message.delete()
        await message.channel.send(f"{message.author.mention}, please refrain from using inappropriate language.")
    await bot.process_commands(message)


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {ctx.author.mention}')

@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name='Member')
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f'{ctx.author.mention}, you have been assigned the {role.name} role.')
    else:
        await ctx.send('Role not found.')

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if ctx.author.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await ctx.send(f'{member.mention} has been kicked from the server.')
    else:
        await ctx.send('You do not have permission to kick members.')

@bot.command()
async def leave(ctx):
    role = discord.utils.get(ctx.guild.roles, name='Member')
    if role:
        await ctx.author.remove_roles(role)
        await ctx.send(f'{ctx.author.mention}, you have been removed from the {role.name} role.')

@bot.command()
@commands.has_role('Member')
async def secret(ctx):
    await ctx.send(f'This is a secret command, {ctx.author.mention}!')
@secret.error
async def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f'Sorry {ctx.author.mention}, you do not have the required role to use this command.')

@bot.command()
async def dm(ctx,*, message):
    await ctx.author.send(f'Message sent to {message}.')


@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="Poll", description=question, color=discord.Color.blue())
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")

@bot.command()
async def reply(ctx, *, message):
    await ctx.reply(f'reply to msg')

bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)