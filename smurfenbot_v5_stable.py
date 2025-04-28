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
CHANNEL_ID = 1366182280661569576
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf', 'OpenSauce', 'TinyKeta', 'Ketaminiac']
GROUP = 'De Smurfen'

BASE_DIR = os.path.dirname(__file__)
BOSSES_FILE = os.path.join(BASE_DIR, 'config/bosses.json')
SKILLS_FILE = os.path.join(BASE_DIR, 'config/skills.json')
CLUES_FILE = os.path.join(BASE_DIR, 'config/clues.json')

# Globale state
TASKS = []
START_STATS = {}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# === Load metadata ===
with open(BOSSES_FILE, 'r') as f:
    BOSSES_DATA = json.load(f)
    # print("[LOAD] Bosses loaded", BOSSES_DATA)
with open(SKILLS_FILE, 'r') as f:
    SKILLS_DATA = json.load(f)
    # print("[LOAD] Skills loaded", SKILLS_DATA)
with open(CLUES_FILE, 'r') as f:
    CLUES_DATA = json.load(f)
    # print("[LOAD] Clues loaded", CLUES_DATA)

# === Generators ===
def generate_boss_tasks(bosses, num_tasks=2):
    print("[GENERATOR] Generating boss tasks...")
    scores = {b['name']: random.random() for b in bosses}
    top = sorted(bosses, key=lambda b: scores[b['name']], reverse=True)[:num_tasks]
    tasks = []
    for b in top:
        amount = random.choice(list(range(5, 55, 5)))
        print(f"[GENERATOR] Boss Task: {b['name']} x{amount}")
        tasks.append({"type": "bosskc", "boss": b['name'], "amount": amount, "category": "Boss KC"})
    return tasks

def generate_exp_tasks(skills, num_tasks=2):
    print("[GENERATOR] Generating exp tasks...")
    chosen = random.sample(skills, num_tasks)
    tasks = []
    for s in chosen:
        amount = random.randrange(s['min_target']//10000, s['max_target']//10000 + 1) * 10000
        print(f"[GENERATOR] EXP Task: {s['name']} {amount} XP")
        tasks.append({"type": "exp", "skill": s['name'], "amount": amount, "category": s.get('category', 'Skilling')})
    return tasks

def generate_clue_tasks(clues, num_tasks=2):
    print("[GENERATOR] Generating clue tasks...")
    chosen = random.sample(clues, num_tasks)
    tasks = []
    for c in chosen:
        amt = random.randint(c.get('min_amount', 1), c.get('max_amount', 3))
        print(f"[GENERATOR] Clue Task: {c['tier']} {amt}")
        tasks.append({"type": "clue", "tier": c['tier'], "amount": amt, "category": "Clue Scrolls"})
    return tasks

# === Hiscores & Utils ===
async def fetch_hiscores(player_name):
    try:
        print(f"[HISCORES] Fetching hiscores for {player_name}")
        user_hs = Highscores(player_name)
        skills = {}
        bosses = {}

        for skill_name, skill_data in user_hs.skill.items():
            skills[skill_name.capitalize()] = int(skill_data['xp']) if skill_data['xp'] != '-1' else 0 

        for boss_name, boss_data in user_hs.boss.items():
            bosses[boss_name.replace('_', ' ').title()] = int(boss_data['kills']) if boss_data['kills'] != '-1' else 0

        print(f"[HISCORES] Done for {player_name}")
        return {"skills": skills, "bosses": bosses}
    except Exception as e:
        print(f"[HISCORES][ERROR] Exception fetching hiscores for {player_name}: {e}")
        return None

def create_progress_bar(pct):
    total = 20
    filled = int((pct / 100) * total)
    return '█' * filled + '—' * (total - filled)

# === Weekly tasks ===
@tasks.loop(hours=168)
async def post_weekly_tasks_loop():
    print("[LOOP] Weekly task loop triggered")
    await generate_weekly_tasks()

async def generate_weekly_tasks():
    print("[COMMAND] Generating new weekly tasks...")
    global TASKS, START_STATS
    channel = bot.get_channel(CHANNEL_ID)
    now = datetime.datetime.now()
    end = now + datetime.timedelta(days=7)

    TASKS = []
    TASKS += generate_boss_tasks(BOSSES_DATA)
    TASKS += generate_exp_tasks(SKILLS_DATA)
    TASKS += generate_clue_tasks(CLUES_DATA)

    print(f"[TASKS] Generated {len(TASKS)} tasks.")

    START_STATS = {}
    for p in PLAYERS:
        data = await fetch_hiscores(p)
        START_STATS[p] = data or {"skills": {}, "bosses": {}}

    embed = discord.Embed(
        title=f"\U0001F3AF Week {now.isocalendar().week} – {GROUP} Start!",
        description=f"🗓 {now:%d/%m/%Y} → {end:%d/%m/%Y}",
        color=0x3498db
    )
    for t in TASKS:
        print(f"[TASK] {t}")
        if t['type'] == 'bosskc':
            embed.add_field(name="⚔️ Boss KC", value=f"Kill {t['boss']} x{t['amount']}", inline=False)
        elif t['type'] == 'exp':
            embed.add_field(name="📚 EXP", value=f"Gain {t['amount']:,} {t['skill']} XP", inline=False)
        elif t['type'] == 'clue':
            embed.add_field(name="🗈️ Clue", value=f"Complete {t['amount']} {t['tier'].capitalize()} clues", inline=False)

    print("[COMMAND] Generation Finished")
    await channel.send(embed=embed)

@tasks.loop(hours=24)
async def daily_progress_update_loop():
    print("[LOOP] Checking progress Daily...")
    await update_progress()

async def update_progress(ctx=None):
    print("[FUNCTION] Checking progress...")
    current = {p: (await fetch_hiscores(p) or {"skills": {}, "bosses": {}}) for p in PLAYERS}
    lines = []
    done = 0

    for t in TASKS:
        print(f"[PROGRESS] Evaluating task: {t}")
        if t['type'] == 'bosskc':
            total = sum(max(current[p]['bosses'].get(t['boss'], 0) - START_STATS[p]['bosses'].get(t['boss'], 0), 0) for p in PLAYERS)
            print(f"[PROGRESS] {t['boss']} KC: {total}/{t['amount']}")
            icon = '✅' if total >= t['amount'] else ('🟠' if total > 0 else '❌')
            
            contrib = []
            for p in PLAYERS:
                gained = max(current[p]['bosses'].get(t['boss'], 0) - START_STATS[p]['bosses'].get(t['boss'], 0), 0)
                if gained > 0:
                    contrib.append((p, gained))
            contrib.sort(key=lambda x: x[1], reverse=True)
            contrib_lines = [f"    • {p}: {g:,}" for p, g in contrib] if contrib else ["    • Geen bijdragen yet"]

            if total >= t['amount']:
                done += 1
                task_line = f"⚔️ Kill {t['boss']} x{t['amount']} ✅\n" + "\n".join(contrib_lines)
            else:
                task_line = f"⚔️ Kill {t['boss']} x{t['amount']} — {total}/{t['amount']} KC {icon}\n" + "\n".join(contrib_lines)
            
            lines.append(task_line)

        elif t['type'] == 'exp':
            total = sum(max(current[p]['skills'].get(t['skill'], 0) - START_STATS[p]['skills'].get(t['skill'], 0), 0) for p in PLAYERS)
            print(f"[PROGRESS] {t['skill']} XP: {total}/{t['amount']}")
            icon = '✅' if total >= t['amount'] else ('🟠' if total > 0 else '❌')

            contrib = []
            for p in PLAYERS:
                gained = max(current[p]['skills'].get(t['skill'], 0) - START_STATS[p]['skills'].get(t['skill'], 0), 0)
                if gained > 0:
                    contrib.append((p, gained))
            contrib.sort(key=lambda x: x[1], reverse=True)
            contrib_lines = [f"    • {p}: {g:,}" for p, g in contrib] if contrib else ["    • Geen bijdragen yet"]

            if total >= t['amount']:
                done += 1
                task_line = f"📚 Gain {t['amount']:,} {t['skill']} XP ✅\n" + "\n".join(contrib_lines)
            else:
                task_line = f"📚 Gain {t['amount']:,} {t['skill']} XP — {total:,}/{t['amount']:,} {icon}\n" + "\n".join(contrib_lines)
            
            lines.append(task_line)


        elif t['type'] == 'clue':
            key = f"Clue Scrolls {t['tier'].capitalize()}"
            total = sum(max(current[p]['skills'].get(key, 0) - START_STATS[p]['skills'].get(key, 0), 0) for p in PLAYERS)
            print(f"[PROGRESS] {t['tier']} clues: {total}/{t['amount']}")
            icon = '✅' if total >= t['amount'] else ('🟠' if total > 0 else '❌')
            if total >= t['amount']:
                done += 1
                task_line = f"🗺️ Complete {t['amount']} {t['tier'].capitalize()} clues ✅"
            else:
                task_line = f"🗺️ Complete {t['amount']} {t['tier'].capitalize()} clues — {total}/{t['amount']} {icon}"
            lines.append(task_line)

    overall = (done / len(TASKS)) * 100 if TASKS else 0
    bar = create_progress_bar(overall)

    # Basistekst
    description = "\n".join(lines) + f"\n\n📈 `{bar}` {overall:.1f}%\n✅ Voltooide taken: {done}/{len(TASKS)}"

    # Als ALLE taken voltooid zijn, voeg proficiat + quote toe
    if done == len(TASKS):
        quotes = [
            "Keep grinding, champion! 💪",
            "Nothing can stop a Smurf when motivated! 🚀",
            "Perfection is not attainable, but if we chase perfection we can catch excellence. ⭐",
            "You did it! Time to flex on the other Smurfs! 🎉",
            "Victory belongs to those who believe. 🎯",
            "One small step for a Smurf, one giant leap for Smurfkind! 🌕",
            "Dream it. Wish it. Do it. 🛠️"
        ]
        chosen_quote = random.choice(quotes)
        description += f"\n\n🏆 **Alle taken voltooid! Proficat!** 🏆\n\n> {chosen_quote}"

    embed = discord.Embed(
        title=f"Smurfen Completionist Progress",
        description=description,
        color=(0x2ecc71 if overall == 100 else (0xf1c40f if overall >= 50 else 0xe74c3c))
    )

    print("[FUNCTION] Progress Update Finished.")

    if ctx:
        await ctx.send(embed=embed)
    else:
        await bot.get_channel(CHANNEL_ID).send(embed=embed)

# === Commands ===
@bot.command()
async def startweek(ctx):
    print("[COMMAND] /startweek triggered")
    await generate_weekly_tasks()
    await ctx.send("✅ Nieuwe week taken gegenereerd!")

@bot.command()
async def starttestweek(ctx):
    print("[COMMAND] /starttestweek triggered (Test Mode)")
    global TASKS, START_STATS
    channel = bot.get_channel(CHANNEL_ID)
    now = datetime.datetime.now()
    end = now + datetime.timedelta(days=7)

    TASKS = [
        {"type": "exp", "skill": "Smithing", "amount": 500, "category": "Skilling"},
        {"type": "exp", "skill": "Mining", "amount": 500, "category": "Skilling"}
    ]

    START_STATS = {}
    for p in PLAYERS:
        data = await fetch_hiscores(p)
        START_STATS[p] = data or {"skills": {}, "bosses": {}}

    embed = discord.Embed(
        title=f"🛠️ TESTWEEK – {GROUP}",
        description=f"🗓 {now:%d/%m/%Y} → {end:%d/%m/%Y}\n\n🎯 Simpele testtaken gegenereerd!",
        color=0xe67e22
    )
    for t in TASKS:
        embed.add_field(name="📚 EXP", value=f"Gain {t['amount']:,} {t['skill']} XP", inline=False)

    await ctx.send("🛠️ **Testweek gestart!** Taken zijn geladen.")
    await channel.send(embed=embed)


@bot.command()
async def progress(ctx):
    print("[COMMAND] /progress triggered.")
    await update_progress(ctx)

@bot.command()
async def progressbar(ctx):
    print("[COMMAND] /progressbar triggered.")
    current_pct = sum(1 for t in TASKS if t.get('completed', False)) / len(TASKS) * 100 if TASKS else 0
    bar = create_progress_bar(current_pct)
    await ctx.send(f"📈 `{bar}` {current_pct:.1f}%")

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    await asyncio.sleep(5)

    now = datetime.datetime.now()

    if not post_weekly_tasks_loop.is_running():
        post_weekly_tasks_loop.start()

    # Check of vandaag maandag is
    if now.weekday() == 0:  # Maandag = 0
        print("[INFO] Vandaag is maandag. Daily progress check wordt niet gestart.")
    else:
        if not daily_progress_update_loop.is_running():
            print("[INFO] Vandaag is NIET maandag. Daily progress check wordt gestart.")
            daily_progress_update_loop.start()
            
    print("[BOT] Ready and loops started!")

bot.run(TOKEN)
