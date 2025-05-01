import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import datetime
import json
import urllib.parse

# === CONFIG ===
TOKEN = 'MTM2NjE4MjcyMTI4OTcxOTg3OA.Ga75j9.-nne1SElnAeTPJQNdvos0lRFjh1oFR0k3bmWik'
GUILD_ID = 1366182078718283848  # Replace with your server ID
CHANNEL_ID = 1366182280661569576  # Replace with the channel where messages are sent
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf']  # Your group ironman RSN's
GROUP = ['De Smurfen']  # Your group ironman Group Name

# Example task list
TASKS = [
    {"type": "drop", "description": "Get a Zilyana Drop", "completed": False},
    {"type": "drop", "description": "Get a Crystal From Cerb", "completed": False},
    {"type": "drop", "description": "Get a Visage", "completed": False},
    {"type": "drop", "description": "Get a Unique from a Raid", "completed": False},
    {"type": "exp", "skill": "Fishing", "amount": 150_000, "gained": 0},
]

START_STATS = {}
HISCORES_API = "https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={}"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    post_weekly_tasks.start()
    daily_progress_update.start()

async def fetch_hiscores(player_name):
    async with aiohttp.ClientSession() as session:
        encoded_name = urllib.parse.quote(player_name)
        async with session.get(HISCORES_API.format(encoded_name)) as resp:
            if resp.status != 200:
                return None
            data = await resp.text()
            return parse_hiscores(data)

def parse_hiscores(raw_data):
    lines = raw_data.split('\n')
    skills = {}
    bosses = {}
    skill_names = [
        'Overall', 'Attack', 'Defence', 'Strength', 'Hitpoints', 'Ranged', 'Prayer', 'Magic',
        'Cooking', 'Woodcutting', 'Fletching', 'Fishing', 'Firemaking', 'Crafting', 'Smithing',
        'Mining', 'Herblore', 'Agility', 'Thieving', 'Slayer', 'Farming', 'Runecraft', 'Hunter', 'Construction'
    ]
    boss_names = ["Kraken", "Callisto", "Zulrah", "Vorkath", "Cerberus", "Commander Zilyana"]

    for i, line in enumerate(lines):
        parts = line.split(',')
        if i < len(skill_names):
            if len(parts) == 3:
                try:
                    rank, level, exp = map(int, parts)
                    skills[skill_names[i]] = exp
                except ValueError:
                    skills[skill_names[i]] = 0
            else:
                skills[skill_names[i]] = 0
        elif 36 <= i-24 <= 36 + len(boss_names):
            boss_index = i - 36
            if boss_index < len(boss_names):
                if len(parts) >= 2:
                    try:
                        rank, kills = map(int, parts[:2])
                        if kills == -1:
                            kills = 0
                        bosses[boss_names[boss_index]] = kills
                    except ValueError:
                        bosses[boss_names[boss_index]] = 0
                else:
                    bosses[boss_names[boss_index]] = 0
    return {"skills": skills, "bosses": bosses}

def calculate_progress(start, current, amount_needed):
    gained = max(current - start, 0)
    percentage = (gained / amount_needed) * 100
    return gained, percentage

@tasks.loop(hours=168)
async def post_weekly_tasks():
    channel = bot.get_channel(CHANNEL_ID)
    now = datetime.datetime.now()
    end = now + datetime.timedelta(days=7)
    task_list = '\n'.join(f"- {task['description'] if task['type'] == 'drop' else f'Get {task['amount']} {task['skill']} EXP'}" for task in TASKS)

    await channel.send(f"Hoi Smurfen! Vandaag start de Smurfen Completionist van Week {now.isocalendar().week} ({now.strftime('%d/%m/%Y')} tot {end.strftime('%d/%m/%Y')})\n\nHier zijn de volgende tasks:\n{task_list}\n\nCurrent progress: 0%\n\nGOOD LUCK!")

    for player in PLAYERS:
        hiscores = await fetch_hiscores(player)
        if hiscores:
            START_STATS[player] = hiscores
            print(f"Hiscores Works: {hiscores}")
        else:
            print(f"Failed to fetch hiscores for {player}")
            START_STATS[player] = {"skills": {}, "bosses": {}}
            print("Hiscores does not work")

@tasks.loop(hours=24)
async def daily_progress_update():
    await update_progress(check_daily=True)

@bot.command()
async def progress(ctx):
    await update_progress(ctx)

@bot.command()
async def startweek(ctx):
    await post_weekly_tasks()
    await ctx.send("New Smurfen Completionist week has been started manually!")

async def update_progress(ctx=None, check_daily=False):
    if not START_STATS:
        if ctx:
            await ctx.send("No active week. Start a new week first!")
        else:
            print("No start stats set yet. Skipping daily progress check.")
        return

    channel = bot.get_channel(CHANNEL_ID)
    combined_progress = []

    total_tasks = len(TASKS)
    completed_tasks = 0

    current_stats = {}
    for player in PLAYERS:
        hiscores = await fetch_hiscores(player)
        if hiscores:
            current_stats[player] = hiscores
        else:
            print(f"Warning: Failed to fetch hiscores for {player}")
            current_stats[player] = {"skills": {}, "bosses": {}}

    for task in TASKS:
        if task["type"] == "drop":
            status = "❌ Not completed"
            combined_progress.append(f"- {task['description']} ({status})")
        elif task["type"] == "exp":
            total_gained = 0
            for player in PLAYERS:
                # print(task["skill"])
                start_exp = START_STATS[player]["skills"].get(task["skill"])
                # print(start_exp)
                now_exp = current_stats[player]["skills"].get(task["skill"])
                gained, _ = calculate_progress(start_exp, now_exp, task["amount"])
                total_gained += gained

            gained, perc = calculate_progress(0, total_gained, task["amount"])

            if gained > 0 and gained >= task["amount"]:
                completed_tasks += 1
                status = f"✅ {gained:,} / {task['amount']:,} EXP (100%)"
            else:
                status = f"❌ {gained:,} / {task['amount']:,} EXP ({perc:.1f}%)"
            combined_progress.append(f"- Get {task['amount']} {task['skill']} EXP: {status}")

    overall_progress = (completed_tasks / total_tasks) * 100

    if ctx:
        await ctx.send(f"Smurfen Progressie Check - Week {datetime.datetime.now().isocalendar().week}\n\n" + '\n'.join(combined_progress) + f"\n\nOverall Progress: {overall_progress:.1f}%")
    elif check_daily:
        await channel.send(f"Hoi Smurfen! Dagelijkse Progressie Check!\n\n" + '\n'.join(combined_progress) + f"\n\nCurrent Progress: {overall_progress:.1f}%\n\nGOGOGO!")

bot.run(TOKEN)