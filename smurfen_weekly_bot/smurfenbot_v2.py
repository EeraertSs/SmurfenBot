import discord
from discord.ext import commands, tasks
from library.osrs_highscores import Highscores
import asyncio
import datetime
import json
import random
import os

# === CONFIG ===
TOKEN = 'MTM2NjE4MjcyMTI4OTcxOTg3OA.Ga75j9.-nne1SElnAeTPJQNdvos0lRFjh1oFR0k3bmWik'
GUILD_ID = 1366182078718283848  # Replace with your server ID
CHANNEL_ID = 1366182280661569576  # Replace with the channel where messages are sent
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf']  # Your group ironman RSN's
GROUP = ['De Smurfen']  # Your group ironman Group Name

TASKS = []
START_STATS = {}
TASK_POOL_FILE = ".../config/task_pool.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

def load_task_pool():
    if not os.path.exists(TASK_POOL_FILE):
        default_tasks = {
            "tasks": [
                {"type": "drop", "description": "Get a Zilyana Drop", "last_picked": None},
                {"type": "drop", "description": "Get a Crystal From Cerberus", "last_picked": None},
                {"type": "drop", "description": "Obtain a Dragon Pickaxe", "last_picked": None},
                {"type": "drop", "description": "Get a Kraken Tentacle", "last_picked": None},
                {"type": "drop", "description": "Get a Visage from Vorkath", "last_picked": None},
                {"type": "drop", "description": "Get a Unique from Chambers of Xeric", "last_picked": None},
                {"type": "exp", "skill": "Fishing", "amount": 150000, "last_picked": None},
                {"type": "exp", "skill": "Strength", "amount": 100000, "last_picked": None},
                {"type": "exp", "skill": "Mining", "amount": 80000, "last_picked": None},
                {"type": "exp", "skill": "Woodcutting", "amount": 90000, "last_picked": None}
            ]
        }
        with open(TASK_POOL_FILE, 'w') as f:
            json.dump(default_tasks, f, indent=4)
    with open(TASK_POOL_FILE, 'r') as f:
        return json.load(f)

def save_task_pool(task_pool):
    with open(TASK_POOL_FILE, 'w') as f:
        json.dump(task_pool, f, indent=4)

async def fetch_hiscores(player_name):
    try:
        user_hs = Highscores(player_name)
        skills = {}
        bosses = {}

        for skill_name, skill_data in user_hs.skill.items():
            skills[skill_name.capitalize()] = int(skill_data['xp']) if skill_data['xp'] != '-1' else 0

        for boss_name, boss_data in user_hs.boss.items():
            bosses[boss_name.replace('_', ' ').title()] = int(boss_data['kills']) if boss_data['kills'] != '-1' else 0

        return {"skills": skills, "bosses": bosses}
    except Exception as e:
        print(f"Exception fetching hiscores for {player_name}: {e}")
        return None

def calculate_progress(start, current, amount_needed):
    gained = max(current - start, 0)
    percentage = (gained / amount_needed) * 100
    return gained, percentage

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    post_weekly_tasks.start()
    daily_progress_update.start()

@tasks.loop(hours=168)
async def post_weekly_tasks():
    global TASKS
    channel = bot.get_channel(CHANNEL_ID)
    now = datetime.datetime.now()
    end = now + datetime.timedelta(days=7)

    task_pool = load_task_pool()
    available_tasks = sorted(task_pool['tasks'], key=lambda x: x['last_picked'] or '1970-01-01')
    selected_tasks = random.sample(available_tasks, 5)
    TASKS = []
    for task in selected_tasks:
        new_task = {k: task[k] for k in task if k in ['type', 'description', 'skill', 'amount']}
        if task['type'] == 'drop':
            new_task['completed'] = False
        elif task['type'] == 'exp':
            new_task['gained'] = 0
        TASKS.append(new_task)
        task['last_picked'] = now.strftime('%Y-%m-%d')
    save_task_pool(task_pool)

    task_list = '\n'.join(f"- {task['description']}" if task['type'] == 'drop' else f"- Get {task['amount']} {task['skill']} EXP" for task in TASKS)
    await channel.send(f"Hoi Smurfen! Vandaag start de Smurfen Completionist van Week {now.isocalendar().week} ({now.strftime('%d/%m/%Y')} tot {end.strftime('%d/%m/%Y')})\n\nHier zijn de volgende tasks:\n{task_list}\n\nCurrent progress: 0%\n\nGOOD LUCK!")

    for player in PLAYERS:
        hiscores = await fetch_hiscores(player)
        if hiscores:
            START_STATS[player] = hiscores
        else:
            print(f"Failed to fetch hiscores for {player}")
            START_STATS[player] = {"skills": {}, "bosses": {}}

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

@bot.command()
async def debug_postweek(ctx):
    await post_weekly_tasks()
    await ctx.send("✅ Debug: New week tasks manually posted.")

@bot.command()
async def debug_dailyprogress(ctx):
    await update_progress(ctx)
    await ctx.send("✅ Debug: Daily progress manually checked.")

@bot.command()
async def hs(ctx, *, player_name: str):
    hiscores = await fetch_hiscores(player_name)
    if hiscores:
        skill_summary = '\n'.join([f"{skill}: {xp:,} XP" for skill, xp in hiscores['skills'].items() if xp > 0])
        await ctx.send(f"Hiscores for **{player_name}**:\n{skill_summary}")
    else:
        await ctx.send(f"❌ Could not fetch hiscores for {player_name}.")

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
                start_exp = START_STATS[player]["skills"].get(task["skill"], 0)
                now_exp = current_stats[player]["skills"].get(task["skill"], 0)
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
