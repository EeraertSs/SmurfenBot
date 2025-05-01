import discord
from discord.ext import commands, tasks
from library.osrs_highscores import Highscores
import asyncio
import datetime
import json
import random
import os

TOKEN = 'MTM2NzQzODcyNTY4NDEzODEyNQ.GAlf8l.QXKBA2cdDbp3wRBmgSrUCVwuMwzShlPw5u1OZY'
CHANNEL_ID = 1367439813241737236
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf']
GROUP = 'De Smurfen'

BASE_DIR = os.path.dirname(__file__)
BOSSES_FILE = os.path.join(BASE_DIR, 'config/updated_bosses.json')
SKILLS_FILE = os.path.join(BASE_DIR, 'config/skills.json')

TASK = None
START_STATS = {}
TASK_END_TIME = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

with open(BOSSES_FILE, 'r') as f:
    BOSSES_DATA = json.load(f)
with open(SKILLS_FILE, 'r') as f:
    SKILLS_DATA = json.load(f)

async def fetch_hiscores(player_name):
    try:
        user_hs = Highscores(player_name)
        skills = {k.capitalize(): int(v['xp']) if v['xp'] != '-1' else 0 for k, v in user_hs.skill.items()}
        bosses = {k.replace('_', ' ').title(): int(v['kills']) if v['kills'] != '-1' else 0 for k, v in user_hs.boss.items()}
        return {"skills": skills, "bosses": bosses}
    except Exception as e:
        print(f"[HISCORES][ERROR] {e}")
        return {"skills": {}, "bosses": {}}

def create_progress_bar(pct):
    total = 20
    filled = int((pct / 100) * total)
    return '█' * filled + '—' * (total - filled)

def generate_hourly_task():
    if random.choice(['exp', 'boss']) == 'exp':
        skill = random.choice(SKILLS_DATA)
        return {
            'type': 'exp',
            'skill': skill['name'],
            'amount': max(1000, int(skill['xp_per_hour'])),
            'category': skill.get('category', 'Skilling')
        }
    else:
        boss = random.choice(BOSSES_DATA)
        kills = max(1, int(boss['kills_per_hour'] * boss.get('group_size', 1)))
        return {
            'type': 'bosskc',
            'boss': boss['name'],
            'amount': kills,
            'category': 'Boss KC'
        }

@bot.command()
async def spin(ctx):
    global TASK, START_STATS, TASK_END_TIME

    TASK = generate_hourly_task()
    START_STATS = {}
    for p in PLAYERS:
        START_STATS[p] = await fetch_hiscores(p)

    TASK_END_TIME = datetime.datetime.now() + datetime.timedelta(hours=1)

    embed = discord.Embed(
        title=f"🎲 Hourly Challenge – {GROUP}",
        description=f"🕒 {datetime.datetime.now():%H:%M} → {TASK_END_TIME:%H:%M}",
        color=0x1abc9c
    )

    if TASK['type'] == 'exp':
        embed.add_field(name=f"📚 Gain {TASK['amount']:,} {TASK['skill']} XP", value="\u200b", inline=False)
    else:
        embed.add_field(name=f"⚔️ Kill {TASK['boss']} x{TASK['amount']}", value="\u200b", inline=False)

    await ctx.send(embed=embed)

    await asyncio.sleep(3600)
    await show_progress(ctx)

@bot.command()
async def progress(ctx):
    if TASK:
        await show_progress(ctx)
    else:
        await ctx.send("❗ Geen actieve task momenteel. Gebruik `/spin` om te starten.")

async def show_progress(ctx):
    current = {p: await fetch_hiscores(p) for p in PLAYERS}
    total = 0
    required = TASK['amount']

    if TASK['type'] == 'exp':
        for p in PLAYERS:
            gained = max(current[p]['skills'].get(TASK['skill'], 0) - START_STATS[p]['skills'].get(TASK['skill'], 0), 0)
            total += gained
        pct = min(100, total / required * 100)
        icon = '✅' if total >= required else ('🟠' if total > 0 else '❌')
        task_line = f"📚 {TASK['skill']} XP: {total:,}/{required:,} {icon}"

    else:
        for p in PLAYERS:
            gained = max(current[p]['bosses'].get(TASK['boss'], 0) - START_STATS[p]['bosses'].get(TASK['boss'], 0), 0)
            total += gained
        pct = min(100, total / required * 100)
        icon = '✅' if total >= required else ('🟠' if total > 0 else '❌')
        task_line = f"⚔️ {TASK['boss']} KC: {total}/{required} {icon}"

    bar = create_progress_bar(pct)
    embed = discord.Embed(
        title=f"🧪 Hourly Progress – {GROUP}",
        description=f"{task_line}\n\n📈 `{bar}` {pct:.1f}%",
        color=(0x2ecc71 if pct == 100 else (0xf1c40f if pct >= 50 else 0xe74c3c))
    )

    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Roulette Bot connected as {bot.user}")

bot.run(TOKEN)
