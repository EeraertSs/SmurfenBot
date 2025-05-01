import discord
from discord.ext import commands
import asyncio
import datetime
import json
import random
import sys
import os

# Voeg het bovenliggende pad toe aan sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from library.osrs_highscores import Highscores

# === CONFIG ===
TOKEN = 'MTM2NzQzODcyNTY4NDEzODEyNQ.GAlf8l.QXKBA2cdDbp3wRBmgSrUCVwuMwzShlPw5u1OZY'
CHANNEL_ID = 1367439813241737236
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf']
GROUP = 'De Smurfen'

BASE_DIR = os.path.dirname(__file__)
BOSSES_FILE = os.path.join(BASE_DIR, '../config/updated_bosses.json')

TASK = None
START_STATS = {}
TASK_END_TIME = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# === LOAD BOSSES ===
with open(BOSSES_FILE, 'r') as f:
    BOSSES_DATA = json.load(f)

# === UTIL FUNCTIES ===
async def fetch_hiscores(player_name):
    try:
        print(f"[HISCORES] Fetching hiscores for {player_name}")
        user_hs = Highscores(player_name)
        bosses = {k.replace('_', ' ').title(): int(v['kills']) if v['kills'] != '-1' else 0 for k, v in user_hs.boss.items()}
        return {"bosses": bosses}
    except Exception as e:
        print(f"[HISCORES][ERROR] {e}")
        return {"bosses": {}}

def create_progress_bar(pct):
    total = 20
    filled = int((pct / 100) * total)
    return '█' * filled + '—' * (total - filled)

def generate_hourly_task():
    boss = random.choice(BOSSES_DATA)
    kills = max(1, int(boss['kills_per_hour'] * boss.get('group_size', 1)))
    print(f"[DEBUG] Geselecteerde boss: {boss['name']}, kills_per_hour: {boss['kills_per_hour']}, group_size: {boss.get('group_size', 1)}, totaal: {kills}")
    return {
        'boss': boss['name'],
        'amount': kills,
        'category': 'Boss KC'
    }

# === COMMANDS ===
@bot.command()
async def spin(ctx):
    global TASK, START_STATS, TASK_END_TIME

    print("[DEBUG] /spin gestart")
    TASK = generate_hourly_task()
    START_STATS = {}

    for p in PLAYERS:
        stats = await fetch_hiscores(p)
        print(f"[DEBUG] Startstats voor {p}: {stats}")
        START_STATS[p] = stats

    TASK_END_TIME = datetime.datetime.now() + datetime.timedelta(hours=1)

    embed = discord.Embed(
        title=f"🎲 Hourly Challenge – {GROUP}",
        description=f"🕒 {datetime.datetime.now():%H:%M} → {TASK_END_TIME:%H:%M}",
        color=0x1abc9c
    )
    embed.add_field(name=f"⚔️ Kill {TASK['boss']} x{TASK['amount']}", value="\u200b", inline=False)

    await ctx.send(embed=embed)
    print("[DEBUG] Task gestart, wacht 1 uur...")
    await asyncio.sleep(3600)
    await show_progress(ctx)

@bot.command()
async def progress(ctx):
    if TASK:
        print("[DEBUG] /progress triggered")
        await show_progress(ctx)
    else:
        await ctx.send("❗ Geen actieve task momenteel. Gebruik `/spin` om te starten.")

# === PROGRESS FUNCTION ===
async def show_progress(ctx):
    print("[DEBUG] Progress check gestart...")
    current = {}

    for p in PLAYERS:
        current[p] = await fetch_hiscores(p)
        print(f"[DEBUG] Current stats voor {p}: {current[p]}")

    total = 0
    required = TASK['amount']
    print(f"[DEBUG] Vereist totaal: {required} kills voor {TASK['boss']}")

    for p in PLAYERS:
        start_kc = START_STATS[p]['bosses'].get(TASK['boss'], 0)
        now_kc = current[p]['bosses'].get(TASK['boss'], 0)
        gained = max(now_kc - start_kc, 0)
        total += gained
        print(f"[DEBUG] {p} progress: {start_kc} → {now_kc} ({gained} kills)")

    pct = min(100, total / required * 100)
    icon = '✅' if total >= required else ('🟠' if total > 0 else '❌')
    task_line = f"⚔️ {TASK['boss']} KC: {total}/{required} {icon}"
    bar = create_progress_bar(pct)
    print(f"[DEBUG] Progress bar: {bar} ({pct:.1f}%)")

    embed = discord.Embed(
        title=f"🧪 Hourly Progress – {GROUP}",
        description=f"{task_line}\n\n📈 `{bar}` {pct:.1f}%",
        color=(0x2ecc71 if pct == 100 else (0xf1c40f if pct >= 50 else 0xe74c3c))
    )

    await ctx.send(embed=embed)

# === BOT READY ===
@bot.event
async def on_ready():
    print(f"✅ Roulette Bot connected as {bot.user}")

bot.run(TOKEN)
