import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import json
import random
import os
import sys

# Voeg het bovenliggende pad toe aan sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from library.osrs_highscores import Highscores

# === CONFIG ===
TOKEN = 'MTM2NjE4MjcyMTI4OTcxOTg3OA.Ga75j9.-nne1SElnAeTPJQNdvos0lRFjh1oFR0k3bmWik'
CHANNEL_ID = 1366182280661569576
PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf', 'TinyKeta', 'Ketaminiac', 'S0l0 Smurf']
# PLAYERS = ['Muziek Smurf', 'Bril Smurf', 'Sukkel Smurf', 'Smul Smurf', 'OpenSauce', 'TinyKeta', 'Ketaminiac']
GROUP = 'De Smurfen'

BASE_DIR = os.path.dirname(__file__)
BOSSES_FILE = os.path.join(BASE_DIR, '../config/temp_bosses.json')
SKILLS_FILE = os.path.join(BASE_DIR, '../config/skills.json')
CLUES_FILE = os.path.join(BASE_DIR, '../config/clues.json')

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
# with open(CLUES_FILE, 'r') as f:
#     CLUES_DATA = json.load(f)
    # print("[LOAD] Clues loaded", CLUES_DATA)

# === Generators ===
def weighted_selection(items, num_select):
    # 1. Eerst alle mandatory items (alwaysIncluded == True)
    mandatory = [i for i in items if i.get('alwaysIncluded', False)]
    
    # 2. Dan de optional items: alles met weight > 0 (alwaysIncluded mag ook terugkomen) // Als Weight niet bestaat, neemt hij 5
    optional = [i for i in items if i.get('weight', 5) > 0]
    
    # 3. Gewichtjes voor optional selection
    weights = [i.get('weight', 5) for i in optional]
    
    # 4. Resultaat starten met mandatory items
    selected = mandatory.copy()

    # 5. Hoeveel extra we nog moeten selecteren
    remaining = num_select - len(selected)

    if remaining > 0 and optional:
        selected += random.choices(optional, weights=weights, k=remaining)

    # 6. Safety: als mandatory er al meer zijn dan num_select, truncate
    return selected[:num_select]


def generate_boss_tasks(bosses, num_tasks=8, players=len(PLAYERS)):
    print("[GENERATOR] Generating boss tasks...")
    total_hours = calculate_total_hours(players=players)
    max_hours_bosskc = total_hours * 0.5  # 50% van totale tijd

    print(f"[DEBUG] Total Available Hours: {total_hours}u")
    print(f"[DEBUG] Max Hours Boss KC (50%): {max_hours_bosskc}u")

    chosen_bosses = weighted_selection(bosses, num_tasks)
    tasks = []
    for b in chosen_bosses:
        group_size = b.get('group_size', 1)
        goal = calculate_boss_goal(
            kills_per_hour=b['kills_per_hour'] * group_size,
            players=players,
            max_hours_bosskc=max_hours_bosskc,
            bosses_count=num_tasks
        )
        time_per_boss = max_hours_bosskc / num_tasks
        print(f"[DEBUG] Boss Task: {b['name']} | Kills/Hour: {b['kills_per_hour']} | Hours Allocated: {time_per_boss} | Goal: {goal} kills")
        tasks.append({"type": "bosskc", "boss": b['name'], "amount": goal, "category": "Boss KC"})
    return tasks

def generate_exp_tasks(skills, num_tasks=3, players=len(PLAYERS)):
    print("[GENERATOR] Generating exp tasks...")
    total_hours = calculate_total_hours(players=players)
    max_hours_exp = total_hours * 0.4  # 40% van totale tijd

    print(f"[DEBUG] Max Hours EXP (40%): {max_hours_exp}u")

    chosen_skills = weighted_selection(skills, num_tasks)

    tasks = []
    for s in chosen_skills:
        goal = calculate_exp_goal(
            xp_per_hour=s['xp_per_hour'],
            players=players,
            max_hours_exp=max_hours_exp,
            skills_count=num_tasks
        )
        time_per_skill = max_hours_exp / num_tasks
        print(f"[DEBUG] EXP Task: {s['name']} | XP/Hour: {s['xp_per_hour']} | Hours Allocated: {time_per_skill} | Goal: {goal:,} XP")
        tasks.append({"type": "exp", "skill": s['name'], "amount": goal, "category": s.get('category', 'Skilling')})
    return tasks


# def generate_clue_tasks(clues, num_tasks=2):
#     print("[GENERATOR] Generating clue tasks...")
#     chosen = random.sample(clues, num_tasks)
#     tasks = []
#     for c in chosen:
#         amt = random.randint(c.get('min_amount', 1), c.get('max_amount', 3))
#         print(f"[GENERATOR] Clue Task: {c['tier']} {amt}")
#         tasks.append({"type": "clue", "tier": c['tier'], "amount": amt, "category": "Clue Scrolls"})
#     return tasks

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

def calculate_total_hours(avg_hours_per_day=2, days_per_week=6, players=4):
    return avg_hours_per_day * days_per_week * players

def calculate_boss_goal(kills_per_hour, players, max_hours_bosskc, bosses_count):
    time_per_boss = max_hours_bosskc / bosses_count
    total_kills = kills_per_hour * time_per_boss
    return max(1, int(total_kills))  # Altijd minstens 1 kill

def calculate_exp_goal(xp_per_hour, players, max_hours_exp, skills_count):
    time_per_skill = max_hours_exp / skills_count
    total_xp = xp_per_hour * time_per_skill
    return max(1000, int(total_xp))  # Altijd minstens 1000 XP


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

    raw_tasks = []
    raw_tasks += generate_boss_tasks(BOSSES_DATA)
    raw_tasks += generate_exp_tasks(SKILLS_DATA)
    # raw_tasks += generate_clue_tasks(CLUES_DATA)

    print(f"[TASKS] Raw Generated {len(raw_tasks)} tasks.")

    # === Combineer dubbele tasks ===
    combined = {}
    for task in raw_tasks:
        if task['type'] == 'bosskc':
            key = f"bosskc:{task['boss']}"
        elif task['type'] == 'exp':
            key = f"exp:{task['skill']}"
        else:
            key = None

        if key:
            if key not in combined:
                combined[key] = task.copy()
            else:
                combined[key]['amount'] += task['amount']

    TASKS = list(combined.values())

    START_STATS = {}
    for p in PLAYERS:
        data = await fetch_hiscores(p)
        START_STATS[p] = data or {"skills": {}, "bosses": {}}

    embed = discord.Embed(
        title=f"🎯 Week {now.isocalendar().week} – {GROUP} Start!",
        description=f"\n\n\n🗓 {now:%d/%m/%Y} → {end:%d/%m/%Y}\n\n",  # Hier wél 3x \n bovenaan
        color=0x3498db
    )



    for t in TASKS:
        print(f"[TASK] {t}")
        if t['type'] == 'bosskc':
            embed.add_field(name=f"⚔️ Kill {t['boss']} x{t['amount']}", value="\u200b", inline=False)
        elif t['type'] == 'exp':
            embed.add_field(name=f"📚 Gain {t['amount']:,} {t['skill']} XP", value="\u200b", inline=False)
        # elif t['type'] == 'clue':
        #     embed.add_field(name="🗈️ Clue", value=f"Complete {t['amount']} {t['tier'].capitalize()} clues", inline=False)

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
    progress_points = []
    done = 0

    for t in TASKS:
        print(f"[PROGRESS] Evaluating task: {t}")
        if t['type'] == 'bosskc':
            total = sum(max(current[p]['bosses'].get(t['boss'], 0) - START_STATS[p]['bosses'].get(t['boss'], 0), 0) for p in PLAYERS)
            pct = min(100, (total / t['amount']) * 100)
            progress_points.append(pct)

            print(f"[PROGRESS] {t['boss']} KC: {total}/{t['amount']}")
            icon = '✅' if total >= t['amount'] else ('🟠' if total > 0 else '❌')

            contrib = []
            for p in PLAYERS:
                gained = max(current[p]['bosses'].get(t['boss'], 0) - START_STATS[p]['bosses'].get(t['boss'], 0), 0)
                if gained > 0:
                    contrib.append((p, gained))
            contrib.sort(key=lambda x: x[1], reverse=True)
            contrib_lines = [f"    • {p}: {g:,}" for p, g in contrib] if contrib else [""]

            if total >= t['amount']:
                done += 1
                task_line = f"⚔️ Kill {t['boss']} ✅\n" + "\n".join(contrib_lines)
            else:
                task_line = f"⚔️ Kill {t['boss']} : {total}/{t['amount']} KC {icon}\n" + "\n".join(contrib_lines)

            lines.append(task_line)

        elif t['type'] == 'exp':
            total = sum(max(current[p]['skills'].get(t['skill'], 0) - START_STATS[p]['skills'].get(t['skill'], 0), 0) for p in PLAYERS)
            pct = min(100, (total / t['amount']) * 100)
            progress_points.append(pct)

            print(f"[PROGRESS] {t['skill']} XP: {total}/{t['amount']}")
            icon = '✅' if total >= t['amount'] else ('🟠' if total > 0 else '❌')

            contrib = []
            for p in PLAYERS:
                gained = max(current[p]['skills'].get(t['skill'], 0) - START_STATS[p]['skills'].get(t['skill'], 0), 0)
                if gained > 0:
                    contrib.append((p, gained))
            contrib.sort(key=lambda x: x[1], reverse=True)
            contrib_lines = [f"    • {p}: {g:,}" for p, g in contrib] if contrib else [""]

            if total >= t['amount']:
                done += 1
                task_line = f"📚 Gain {t['skill']} XP ✅\n" + "\n".join(contrib_lines)
            else:
                task_line = f"📚 Gain {t['skill']} XP : {total:,}/{t['amount']:,} {icon}\n" + "\n".join(contrib_lines)

            lines.append(task_line)

    # Hier nieuw: gemeten op basis van % progressie over taken
    overall = sum(progress_points) / len(progress_points) if progress_points else 0
    bar = create_progress_bar(overall)

    description = "\n".join(lines) + f"\n\n📈 `{bar}` {overall:.1f}%\n\n✅ Completed: {done}/{len(TASKS)}"

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
        {"type": "exp", "skill": "Mining", "amount": 500, "category": "Skilling"},
        {"type": "bosskc", "boss": "Zulrah", "amount": 2, "category": "Boss KC"}
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
        if t['type'] == 'exp':
            embed.add_field(name="📚 EXP", value=f"Gain {t['amount']:,} {t['skill']} XP", inline=False)
        elif t['type'] == 'bosskc':
            embed.add_field(name="⚔️ Boss KC", value=f"Kill {t['boss']} x{t['amount']}", inline=False)

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
