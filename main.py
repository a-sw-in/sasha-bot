import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import time
import requests
import urllib.parse
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')

@bot.command(name="assign")
async def assign(ctx, admission_number: str):
    if ctx.guild is None:
        await ctx.send("This command must be used in a server.")
        return

    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID or not AIRTABLE_TABLE_NAME:
        await ctx.send("Error occured contact admin.")
        return

    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    def airtable_request(method, url, headers, params=None, json=None, attempts=3, timeout=15):
        """Make an HTTP request to Airtable with simple retry/backoff for transient errors."""
        for attempt in range(1, attempts + 1):
            try:
                return requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)
            except requests.exceptions.ReadTimeout:
                logging.warning('Airtable read timeout (attempt %d/%d)', attempt, attempts)
                if attempt == attempts:
                    raise
                time.sleep(0.5 * attempt)
            except requests.RequestException:
                logging.exception('Airtable request exception on attempt %d', attempt)
                if attempt == attempts:
                    raise
                time.sleep(0.5 * attempt)

    table_quoted = urllib.parse.quote(AIRTABLE_TABLE_NAME, safe='')
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_quoted}'
    formula = f"LOWER({{Admission}}) = '{admission_number.strip().lower()}'"
    # First: check if the sender is already registered by Discord ID in common field names.
    # Check whether the sender is already registered by Discord ID in common field names.
    # If Airtable returns 422 (bad formula), log and continue to admission check instead of failing.
    user_id_str = str(ctx.author.id)
    # Check each possible Discord ID field separately to avoid formula errors with OR.
    discord_fields = ['DiscordID', 'Discord Id', 'discord_id']
    try:
        for field in discord_fields:
            formula = f"{{{field}}} = '{user_id_str}'"
            r_check = airtable_request('GET', url, headers=headers, params={'filterByFormula': formula, 'maxRecords': 1}, timeout=15)
            if r_check.status_code == 200:
                rdata = r_check.json()
                if rdata.get('records'):
                    await ctx.send(f'{ctx.author.mention}, you have already registered.')
                    return
            elif r_check.status_code == 422:
                logging.error('Airtable discord-id check formula invalid for field %s (422): %s', field, r_check.text)
                continue
            else:
                logging.error('Airtable discord-check returned %s for field %s: %s', r_check.status_code, field, r_check.text)
                await ctx.send(f'Failed to query Airtable (status {r_check.status_code}).')
                return
    except requests.RequestException:
        logging.exception('Airtable discord-id check failed')
        await ctx.send('Failed to query Airtable (network error).')
        return

    formula = f"LOWER({{Admission}}) = '{admission_number.strip().lower()}'"
    try:
        resp = airtable_request('GET', url, headers=headers, params={'filterByFormula': formula, 'maxRecords': 1}, timeout=15)
        if resp.status_code != 200:
            logging.error('Airtable returned %s: %s', resp.status_code, resp.text)
            await ctx.send(f'Failed contact admin.')
            return
    except requests.RequestException:
        logging.exception('Airtable request failed')
        await ctx.send('Failed contact admin.')
        return

    data = resp.json()
    records = data.get('records', [])
    if not records:
        await ctx.send('Not a valid admission number.')
        return

    record = records[0]
    fields = record.get('fields', {})
    discord_id = fields.get('DiscordID') or fields.get('Discord Id') or fields.get('discord_id')
    if discord_id:
        await ctx.send(f'Admission `{admission_number}` is already registered (contact admin).')
        return

    record_id = record.get('id')
    if not record_id:
        await ctx.send('Failed to retrieve record ID (contact admin).')
        return

    try:
        patch_url = f"{url}/{record_id}"
        payload = {'fields': {'DiscordID': str(ctx.author.id), 'Name': ctx.author.display_name}}
        p = airtable_request('PATCH', patch_url, headers=headers, json=payload, timeout=15)
        if p.status_code not in (200, 201):
            logging.error('Airtable PATCH returned %s: %s', p.status_code, p.text)
            await ctx.send(f'Failed to register (status {p.status_code}).')
            return
        await ctx.send(f'Success — {ctx.author.mention} registered for `{admission_number}`.')
        role = discord.utils.get(ctx.guild.roles, name='Member')
        if role:
            await ctx.author.add_roles(role)
            await ctx.send(f'{ctx.author.mention}, you are now a member of KULT Esports!!')
        else:
            await ctx.send('Role not found.')

    except requests.RequestException:
        logging.exception('Failed to update Airtable')
        await ctx.send('Failed to register you (network error).')





@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if ctx.author.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await ctx.send(f'{member.mention} has been kicked from the server.')
    else:
        await ctx.send('You do not have permission to kick members.')
















if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_TOKEN not set in .env")
    else:
        bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)

