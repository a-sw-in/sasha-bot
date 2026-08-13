import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import re


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')


# ============================================================
# LOGGING
# ============================================================

handler = logging.FileHandler(
    filename='discord.log',
    encoding='utf-8',
    mode='w'
)


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ============================================================
# BOT
# ============================================================

bot = commands.Bot(
    command_prefix='!',
    intents=intents
)


# ============================================================
# BANNED WORDS
# ============================================================

banned_words = [
    'fuck',
    'pussy',
    'motherfucker',
    'poorimone',
    'thayoli',
    'shit',
    'bitch',
    'asshole',
    'dick',
    'cunt'
]

pattern = re.compile(
    r"\b(?:" +
    "|".join(re.escape(w) for w in banned_words) +
    r")\b",
    re.IGNORECASE
)


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    channel = discord.utils.get(
        member.guild.text_channels,
        name='welcome'
    )

    if channel:
        await channel.send(
            f'Welcome to the KULT Esports, {member.mention}!'
        )


# ============================================================
# KICK COMMAND
# ============================================================

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):

    if ctx.author.guild_permissions.kick_members:

        await member.kick(
            reason=reason
        )

        await ctx.send(
            f'{member.mention} has been kicked from the server.'
        )

    else:

        await ctx.send(
            'You do not have permission to kick members.'
        )


# ============================================================
# SECRET COMMAND
# ============================================================

@bot.command()
@commands.has_role('Member')
async def secret(ctx, *, message):

    await ctx.send(
        f'{message}'
    )


@secret.error
async def secret_error(ctx, error):

    if isinstance(
        error,
        commands.MissingRole
    ):

        await ctx.send(
            f'Sorry {ctx.author.mention}, you do not have the required role to use this command.'
        )


# ============================================================
# DM COMMAND
# ============================================================

@bot.command()
async def dm(ctx, *, message):

    await ctx.author.send(
        f'Message sent to {message}.'
    )


# ============================================================
# POLL COMMAND
# ============================================================

@bot.command()
async def poll(ctx, *, question):

    embed = discord.Embed(
        title="KULT Esports",
        description=question,
        color=discord.Color.blue()
    )

    poll_message = await ctx.send(
        embed=embed
    )

    await poll_message.add_reaction(
        "👍"
    )

    await poll_message.add_reaction(
        "👎"
    )


# ============================================================
# REPLY COMMAND
# ============================================================

@bot.command()
async def reply(ctx, *, message):

    await ctx.reply(
        f'reply to msg'
    )


# ============================================================
# MESSAGE HANDLER
# ============================================================

@bot.event
async def on_message(message):

    # Ignore bot messages
    if message.author.bot:
        return

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    if message.content.startswith(
        bot.command_prefix
    ):

        await bot.process_commands(
            message
        )

        return

    # --------------------------------------------------------
    # SASHA
    # --------------------------------------------------------

    if "sasha" in message.content.lower():

        await message.channel.send(
            f"{message.author.mention}, I am here buddy, how can I help you?"
        )

    # --------------------------------------------------------
    # BANNED WORD FILTER
    # --------------------------------------------------------

    if (
        message.guild
        and pattern.search(
            message.content or ""
        )
    ):

        try:

            await message.delete()

            await message.channel.send(
                f"{message.author.mention}, please refrain from using inappropriate language."
            )

        except discord.Forbidden:

            logging.warning(
                'Missing permissions to delete messages in %s',
                message.guild
            )

        except Exception:

            logging.exception(
                'Failed to delete message'
            )

        return

    # --------------------------------------------------------
    # PROCESS COMMANDS
    # --------------------------------------------------------

    await bot.process_commands(
        message
    )


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    token = (
        TOKEN or ''
    ).strip().strip('"').strip("'")

    if not token:

        print("DISCORD_TOKEN not set in .env")

    else:

        bot.run(
            token,
            log_handler=handler,
            log_level=logging.DEBUG
        )
