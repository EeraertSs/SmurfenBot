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
GUILD_ID = 1366182078718283848
CHANNEL_ID = 1366182280661569576
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf']
GROUP = ['De Smurfen']

TASKS = []
START_STATS = {}
TASK_POOL_FILE = ".../config/task_pool.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Laad en bewaar taken
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

# Fetch highscores
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

def create_progress_bar(percentage):
    total_blocks = 10
    filled_blocks = int((percentage / 100) * total_blocks)
    return '█' * filled_blocks + '-' * (total_blocks - filled_blocks)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is verbonden met Discord!")

    if not post_weekly_tasks_loop.is_running():
        post_weekly_tasks_loop.start()
        print("🛎️ post_weekly_tasks_loop gestart.")

    if not daily_progress_update.is_running():
        daily_progress_update.start()
        print("🛎️ daily_progress_update gestart.")

    print(f"🎯 Klaar om tasks te posten in '{bot.get_guild(GUILD_ID)}'.")

# ----------------------------

@tasks.loop(hours=168)
async def post_weekly_tasks_loop():
    await post_weekly_tasks()

# ----------------------------

async def post_weekly_tasks(manual=False):
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

    # Embed maken
    embed = discord.Embed(
        title=f"🎯 Week {now.isocalendar().week} - Smurfen Completionist Start!",
        description=f"📅 Periode: {now.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}\n👥 Groep: {GROUP[0]}",
        color=0x3498db
    )

    for task in TASKS:
        if task['type'] == 'drop':
            embed.add_field(name="🎯 Drop Task", value=f"**{task['description']}**", inline=False)
        elif task['type'] == 'exp':
            embed.add_field(name="🎯 EXP Task", value=f"**Get {task['amount']} {task['skill']} EXP**", inline=False)

    embed.set_footer(text="Good luck, Smurfen! 🍀")

    if manual:
        await channel.send(embed=embed)
    else:
        with open('img/osrslogo.jpg', 'rb') as f:
            file = discord.File(f, filename='osrslogo.jpg')
            embed.set_thumbnail(url='attachment://osrslogo.jpg')
            await channel.send(file=file, embed=embed)

    # Start stats opslaan
    for player in PLAYERS:
        hiscores = await fetch_hiscores(player)
        if hiscores:
            START_STATS[player] = hiscores
        else:
            print(f"❌ Failed to fetch hiscores for {player}")
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

@bot.command()
async def hsdetail(ctx, *, player_name: str):
    hiscores = await fetch_hiscores(player_name)
    if hiscores:
        bosses = hiscores['bosses']
        boss_text = ""
        for boss, kc in bosses.items():
            if kc > 0:
                boss_text += f"**{boss}**: {kc} kills\n"

        if boss_text == "":
            boss_text = "No boss kill data found."

        embed = discord.Embed(title=f"🏆 Boss Killcount - {player_name}", color=0x9b59b6)
        embed.add_field(name="Bosses", value=boss_text, inline=False)
        embed.set_footer(text="Only bosses with kills are shown.")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Could not fetch boss hiscores for {player_name}.")

@bot.command()
async def starttestweek(ctx):
    global TASKS
    channel = bot.get_channel(CHANNEL_ID)
    now = datetime.datetime.now()
    end = now + datetime.timedelta(days=7)

    TASKS = [
        {"type": "exp", "skill": "Fishing", "amount": 500, "gained": 0},
        {"type": "exp", "skill": "Woodcutting", "amount": 300, "gained": 0},
        {"type": "exp", "skill": "Fletching", "amount": 100, "gained": 0}
    ]

    embed = discord.Embed(
        title=f"🧪 Test Week {now.isocalendar().week} - Smurfen Testweek Actief!",
        description=f"📅 Periode: {now.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}\n👥 Groep: {GROUP[0]}",
        color=0xf1c40f
    )

    
    for task in TASKS:
        embed.add_field(name="🎯 EXP Task", value=f"**Get {task['amount']} {task['skill']} EXP**", inline=False)

    embed.set_footer(text="Good luck, Smurfen! 🍀")

    await channel.send(embed=embed)

    # Start stats opslaan
    for player in PLAYERS:
        hiscores = await fetch_hiscores(player)
        if hiscores:
            START_STATS[player] = hiscores
        else:
            print(f"Failed to fetch hiscores for {player}")
            START_STATS[player] = {"skills": {}, "bosses": {}}

    await ctx.send("✅ Testweek taken ingesteld. Log snel in op RS en begin te smurfen! 🎣🌳🏹")

async def update_progress(ctx=None, check_daily=False):
    if not START_STATS:
        if ctx:
            await ctx.send("No active week. Start a new week first!")
        else:
            print("No start stats set yet. Skipping daily progress check.")
        return

    channel = bot.get_channel(CHANNEL_ID)
    embed = discord.Embed(title=f"Smurfen Completionist Progress - Week {datetime.datetime.now().isocalendar().week}", color=0x00ff00)

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
            icon = "🟠" if not task["completed"] else "✅"
            embed.add_field(name=f"{icon} {task['description']}", value="Drop Task", inline=False)
        elif task["type"] == "exp":
            total_gained = 0
            for player in PLAYERS:
                start_exp = START_STATS[player]["skills"].get(task["skill"], 0)
                now_exp = current_stats[player]["skills"].get(task["skill"], 0)
                gained, _ = calculate_progress(start_exp, now_exp, task["amount"])
                total_gained += gained

            gained, perc = calculate_progress(0, total_gained, task["amount"])
            if gained >= task["amount"]:
                icon = "✅"
                completed_tasks += 1
            elif gained > 0:
                icon = "🟠"
            else:
                icon = "❌"
            embed.add_field(name=f"{icon} Get {task['amount']} {task['skill']} EXP", value=f"{gained:,} / {task['amount']:,} EXP ({perc:.1f}%)", inline=False)

    overall_progress = (completed_tasks / total_tasks) * 100
    progress_bar = create_progress_bar(overall_progress)
    embed.add_field(name="Overall Progress", value=f"`{progress_bar}` {overall_progress:.1f}%", inline=False)

    if ctx:
        await ctx.send(embed=embed)
    elif check_daily:
        await channel.send(embed=embed)

@bot.command()
async def resetweek(ctx):
    global TASKS, START_STATS
    TASKS = []
    START_STATS = {}
    await ctx.send("♻️ Alle taken en progressie zijn gereset. Klaar voor een nieuwe start!")

@bot.command()
async def progressbar(ctx):
    if not TASKS:
        await ctx.send("⚠️ Er zijn momenteel geen actieve tasks.")
        return

    total_tasks = len(TASKS)
    completed = 0

    for task in TASKS:
        if task.get('type') == 'drop' and task.get('completed', False):
            completed += 1
        elif task.get('type') == 'exp':
            progress = task.get('gained', 0) / task.get('amount', 1)
            if progress >= 1:
                completed += 1

    percent = int((completed / total_tasks) * 100)
    filled = int(percent / 5)  # 20 blokjes
    bar = "█" * filled + "—" * (20 - filled)

    embed = discord.Embed(
        title="📊 Smurfen Progressie",
        description=f"[{bar}] {percent}% voltooid",
        color=0x2ecc71 if percent == 100 else 0xf1c40f
    )
    await ctx.send(embed=embed)

bot.run(TOKEN)
