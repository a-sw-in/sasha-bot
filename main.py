import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import time
import requests
import urllib.parse
import re

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')


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
# AIRTABLE REQUEST FUNCTION
# ============================================================

def airtable_request(
    method,
    url,
    headers,
    params=None,
    json=None,
    attempts=3,
    timeout=15
):
    """
    Make an HTTP request to Airtable with simple
    retry/backoff for transient errors.
    """

    for attempt in range(1, attempts + 1):

        try:

            return requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json,
                timeout=timeout
            )

        except requests.exceptions.ReadTimeout:

            logging.warning(
                'Airtable read timeout (attempt %d/%d)',
                attempt,
                attempts
            )

            if attempt == attempts:
                raise

            time.sleep(0.5 * attempt)

        except requests.RequestException:

            logging.exception(
                'Airtable request exception on attempt %d',
                attempt
            )

            if attempt == attempts:
                raise

            time.sleep(0.5 * attempt)


# ============================================================
# ASSIGN COMMAND
# ============================================================

@bot.command(name="assign")
async def assign(ctx, admission_number: str):

    if ctx.guild is None:
        await ctx.send("This command must be used in a server.")
        return

    if (
        not AIRTABLE_API_KEY
        or not AIRTABLE_BASE_ID
        or not AIRTABLE_TABLE_NAME
    ):
        await ctx.send("Error occured contact admin.")
        return

    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    # --------------------------------------------------------
    # AIRTABLE URL
    # --------------------------------------------------------

    table_quoted = urllib.parse.quote(
        AIRTABLE_TABLE_NAME,
        safe=''
    )

    url = (
        f'https://api.airtable.com/v0/'
        f'{AIRTABLE_BASE_ID}/'
        f'{table_quoted}'
    )

    # --------------------------------------------------------
    # CHECK IF USER IS ALREADY REGISTERED
    # --------------------------------------------------------

    user_id_str = str(ctx.author.id)

    discord_fields = [
        'DiscordID',
        'Discord Id',
        'discord_id'
    ]

    try:

        for field in discord_fields:

            formula = (
                f"{{{field}}} = "
                f"'{user_id_str}'"
            )

            r_check = airtable_request(
                'GET',
                url,
                headers=headers,
                params={
                    'filterByFormula': formula,
                    'maxRecords': 1
                },
                timeout=15
            )

            if r_check.status_code == 200:

                rdata = r_check.json()

                if rdata.get('records'):

                    await ctx.send(
                        f'{ctx.author.mention}, you have already registered.'
                    )

                    return

            elif r_check.status_code == 422:

                logging.error(
                    'Airtable discord-id check formula invalid '
                    'for field %s (422): %s',
                    field,
                    r_check.text
                )

                continue

            else:

                logging.error(
                    'Airtable discord-check returned %s '
                    'for field %s: %s',
                    r_check.status_code,
                    field,
                    r_check.text
                )

                await ctx.send(
                    f'Failed to query Airtable '
                    f'(status {r_check.status_code}).'
                )

                return

    except requests.RequestException:

        logging.exception(
            'Airtable discord-id check failed'
        )

        await ctx.send(
            'Failed to query Airtable (network error).'
        )

        return

    # --------------------------------------------------------
    # SEARCH ADMISSION NUMBER
    # --------------------------------------------------------

    admission_value = (
        admission_number
        .strip()
        .lower()
    )

    # Escape single quotes for Airtable formula
    admission_value = admission_value.replace(
        '\\',
        '\\\\'
    ).replace(
        "'",
        "\\'"
    )

    formula = (
        f"LOWER({{Admission}}) = "
        f"'{admission_value}'"
    )

    try:

        resp = airtable_request(
            'GET',
            url,
            headers=headers,
            params={
                'filterByFormula': formula,
                'maxRecords': 1
            },
            timeout=15
        )

        if resp.status_code != 200:

            logging.error(
                'Airtable returned %s: %s',
                resp.status_code,
                resp.text
            )

            await ctx.send(
                f'Failed contact admin.'
            )

            return

    except requests.RequestException:

        logging.exception(
            'Airtable request failed'
        )

        await ctx.send(
            'Failed contact admin.'
        )

        return

    # --------------------------------------------------------
    # PROCESS RESPONSE
    # --------------------------------------------------------

    data = resp.json()

    records = data.get(
        'records',
        []
    )

    if not records:

        await ctx.send(
            'Not a valid admission number.'
        )

        return

    record = records[0]

    fields = record.get(
        'fields',
        {}
    )

    # --------------------------------------------------------
    # CHECK IF ADMISSION ALREADY REGISTERED
    # --------------------------------------------------------

    discord_id = (
        fields.get('DiscordID')
        or fields.get('Discord Id')
        or fields.get('discord_id')
    )

    if discord_id:

        await ctx.send(
            f'Admission `{admission_number}` '
            f'is already registered (contact admin).'
        )

        return

    # --------------------------------------------------------
    # GET RECORD ID
    # --------------------------------------------------------

    record_id = record.get(
        'id'
    )

    if not record_id:

        await ctx.send(
            'Failed to retrieve record ID (contact admin).'
        )

        return

    # --------------------------------------------------------
    # UPDATE AIRTABLE
    # --------------------------------------------------------

    try:

        patch_url = (
            f"{url}/{record_id}"
        )

        payload = {
            'fields': {
                'DiscordID': str(ctx.author.id),
                'Name': ctx.author.display_name
            }
        }

        p = airtable_request(
            'PATCH',
            patch_url,
            headers=headers,
            json=payload,
            timeout=15
        )

        if p.status_code not in (200, 201):

            logging.error(
                'Airtable PATCH returned %s: %s',
                p.status_code,
                p.text
            )

            await ctx.send(
                f'Failed to register '
                f'(status {p.status_code}).'
            )

            return

        # ----------------------------------------------------
        # SUCCESS MESSAGE
        # ----------------------------------------------------

        await ctx.send(
            f'Success — {ctx.author.mention} '
            f'registered for `{admission_number}`.'
        )

        # ----------------------------------------------------
        # GIVE MEMBER ROLE
        # ----------------------------------------------------

        role = discord.utils.get(
            ctx.guild.roles,
            name='Member'
        )

        if role:

            await ctx.author.add_roles(
                role
            )

            await ctx.send(
                f'{ctx.author.mention}, '
                f'you are now a member of KULT Esports!!'
            )

        else:

            await ctx.send(
                'Role not found.'
            )

    except requests.RequestException:

        logging.exception(
            'Failed to update Airtable'
        )

        await ctx.send(
            'Failed to register you (network error).'
        )


# ============================================================
# KICK COMMAND
# ============================================================

@bot.command()
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason=None
):

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
async def secret(
    ctx,
    *,
    message
):

    await ctx.send(
        f'{message}'
    )


@secret.error
async def secret_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.MissingRole
    ):

        await ctx.send(
            f'Sorry {ctx.author.mention}, '
            f'you do not have the required role '
            f'to use this command.'
        )


# ============================================================
# DM COMMAND
# ============================================================

@bot.command()
async def dm(
    ctx,
    *,
    message
):

    await ctx.author.send(
        f'Message sent to {message}.'
    )


# ============================================================
# POLL COMMAND
# ============================================================

@bot.command()
async def poll(
    ctx,
    *,
    question
):

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
async def reply(
    ctx,
    *,
    message
):

    await ctx.reply(
        f'reply to msg'
    )


# ============================================================
# MESSAGE EVENT
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
    # BAD WORD FILTER
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

        retry_delay = 60
        max_retry_delay = 900

        while True:

            try:

                bot.run(
                    token,
                    log_handler=handler,
                    log_level=logging.DEBUG
                )

                break

            except discord.HTTPException as exc:

                if exc.status == 429:

                    logging.warning(
                        "Discord login rate-limited (429). "
                        "Retrying in %s seconds.",
                        retry_delay
                    )

                    time.sleep(
                        retry_delay
                    )

                    retry_delay = min(
                        retry_delay * 2,
                        max_retry_delay
                    )

                    # Recreate the bot after bot.run() exits
                    bot = commands.Bot(
                        command_prefix='!',
                        intents=intents
                    )

                    # Re-register events/commands is required
                    # if the bot object is recreated, so raise
                    # instead of silently starting an empty bot.
                    raise

                raise
