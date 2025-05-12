import discord
from discord.ext import commands
import asyncio
import json
import os
import sys

# Voeg het bovenliggende pad toe aan sys.path als je de highscores module zelf hebt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from library.osrs_highscores import Highscores

# === CONFIG ===
TOKEN = 'MTM2NzQzODcyNTY4NDEzODEyNQ.GAlf8l.QXKBA2cdDbp3wRBmgSrUCVwuMwzShlPw5u1OZY'
CHANNEL_ID = 1368553208292577380  # <- Vervang dit met het juiste kanaal-ID
PLAYER = 'Sukkel Smurf'

# === Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Vereisten voor elite diaries + boostable flag
ELITE_REQUIREMENTS = {
    "Attack": (70, False),
    "Strength": (76, True),
    "Defence": (70, False),
    "Ranged": (70, True),
    "Prayer": (85, False),
    "Magic": (96, True),
    "Runecrafting": (91, True),
    "Construction": (78, True),
    "Hitpoints": (70, False),
    "Agility": (90, True),
    "Herblore": (90, True),
    "Thieving": (91, False),
    "Crafting": (85, True),
    "Fletching": (95, True),
    "Slayer": (95, True),
    "Hunter": (70, False),
    "Mining": (85, True),
    "Smithing": (91, True),
    "Fishing": (96, True),
    "Cooking": (95, True),
    "Firemaking": (85, True),
    "Woodcutting": (90, True),
    "Farming": (91, True)
}

async def fetch_hiscores(player_name):
    try:
        user_hs = Highscores(player_name)
        skills = {k.capitalize(): int(v['level']) if v['level'] != '-1' else 0 for k, v in user_hs.skill.items()}
        return skills
    except Exception as e:
        print(f"[ERROR] Could not fetch hiscores: {e}")
        return {}

def get_missing_requirements(current_stats): 
    missing = {}
    for skill, (required, boostable) in ELITE_REQUIREMENTS.items():
        current = current_stats.get(skill, 0)
        needed_level = required if not boostable else max(required - 5, 1)
        if current < needed_level:
            missing[skill] = (current, required, boostable)
    return missing

@bot.command()
async def elite(ctx):
    await ctx.send("📊 Fetching stats from hiscores...")
    stats = await fetch_hiscores(PLAYER)
    if not stats:
        await ctx.send("❌ Error fetching stats.")
        return

    >Qssing = get_missing_requirements(stats)')'

    if not missing:
        await ctx.send(f"✅ {PLAYER} has met all elite diary requirements!")
        return

    lines = [
        f"❗ **{skill}**: {lvl} / {required} {'(boostable)' if boost else '(no boost)'}"
        for skill, (lvl, required, boost) in sorted(missing.items())
    ]

    embed = discord.Embed(
        title=f"🧾 Elite Diary Tracker – {PLAYER}",
        description="\n".join(lines),
        color=0xe74c3c
    )
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Elite Diary Bot ready as {bot.user}")

bot.run(TOKEN)