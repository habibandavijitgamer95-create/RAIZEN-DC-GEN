import discord
from discord import app_commands
from discord.ext import commands
import os, sqlite3, random, string
from flask import Flask
from threading import Thread

# --- 🌐 KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- ⚙️ CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
FREE_CH = 1479204587104895060
PREMIUM_CH = 1479080682616520718
PAID_CH = 1479080682616520717
LOG_CH = 1479239531499880628 
STAFF_IDS = [1242372804859400195, 1406599824089808967, 1040256699480686604]
BASE_PATH = "categories"

# 🛠️ Directory Error Fix
if os.path.exists(BASE_PATH) and not os.path.isdir(BASE_PATH):
    os.remove(BASE_PATH) # যদি ফাইল হিসেবে থাকে তবে ডিলিট করবে
if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH, exist_ok=True)

# --- 🗄️ DATABASE ---
db = sqlite3.connect("bot_data.db", check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL;") 
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS tickets (code TEXT PRIMARY KEY, service TEXT, account TEXT, tier TEXT)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Raizen Bot Linked!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def get_count(service):
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    if os.path.exists(path) and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    return 0

# --- 🚀 ALL COMMANDS (List from your Screenshots) ---

# 👤 MEMBER COMMANDS
@bot.tree.command(name="profile", description="View profile & stats")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (target.id,))
    row = cursor.fetchone()
    gens, vouches = (row[0], row[1]) if row else (0, 0)
    
    embed = discord.Embed(title=f"👤 {target.name}'s Profile", color=0x00aaff)
    embed.add_field(name="📦 Accounts Generated", value=f"`{gens}`", inline=True)
    embed.add_field(name="⭐ Total Vouches", value=f"`{vouches}`", inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stock", description="View available stock")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Stock — All", color=0xFFFFFF)
    sections = {
        "🟢 FREE": ["Bin", "Crunchyroll", "Disney", "Hbomax", "Hotmail", "Netflix", "Paramount", "Spotify", "Xbox"],
        "🟣 PREMIUM": ["Dazn", "Disney", "Netflix", "Steam"],
        "🟡 PAID": ["test2"]
    }
    for title, cats in sections.items():
        val = ""
        for cat in cats: val += f"░░░░░ **{cat}** — {get_count(cat)} accounts\n"
        embed.add_field(name=title, value=val, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gen", description="Generate a 4-digit ticket code")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    if interaction.user.id not in STAFF_IDS:
        ch_map = {"free": FREE_CH, "premium": PREMIUM_CH, "paid": PAID_CH}
        if interaction.channel_id != ch_map.get(tier.value):
            return await interaction.response.send_message(f"❌ Use <#{ch_map.get(tier.value)}>", ephemeral=True)

    service_name = service.capitalize()
    path = f"{BASE_PATH}/{service_name}.txt"
    if get_count(service_name) == 0:
        return await interaction.response.send_message("⚠️ Out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    t_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cursor.execute("INSERT INTO tickets (code, service, account, tier) VALUES (?, ?, ?, ?)", (t_code, service_name, acc, tier.name))
    db.commit()
    await interaction.response.send_message(f"🎫 Ticket: **{t_code}**\nUse `/redeem` to claim!", ephemeral=True)

# 🛡️ STAFF COMMANDS
@bot.tree.command(name="add", description="Add accounts (attach .txt)")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True) # টাইমআউট ফিক্স
    try:
        content = await file.read()
        lines = content.decode("utf-8").splitlines()
        valid = [l for l in lines if l.strip()]
        
        path = f"{BASE_PATH}/{service.capitalize()}.txt"
        with open(path, "a", encoding="utf-8") as f:
            for acc in valid: f.write(acc + "\n")
        
        await interaction.followup.send(f"✅ Added `{len(valid)}` accounts to **{service.capitalize()}**")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="redeem", description="Validate a ticket code")
async def redeem(interaction: discord.Interaction, code: str):
    code = code.upper()
    cursor.execute("SELECT service, account, tier FROM tickets WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        service, account, tier = row
        cursor.execute("DELETE FROM tickets WHERE code = ?", (code,))
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        cursor.execute("UPDATE users SET gens = gens + 1 WHERE user_id = ?", (interaction.user.id,))
        db.commit()
        try:
            await interaction.user.send(f"🎁 **Claimed!**\nService: {service}\nTier: {tier}\nAccount: `{account}`")
            await interaction.response.send_message(f"✅ Valid! Category: **{tier}**. Check DMs!", ephemeral=True)
        except: await interaction.response.send_message("❌ DM Closed!", ephemeral=True)
    else: await interaction.response.send_message("❌ Invalid Code!", ephemeral=True)

@bot.tree.command(name="addv", description="Manually add vouches")
async def addv(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("Staff only!", ephemeral=True)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,))
    cursor.execute("UPDATE users SET vouches = vouches + ? WHERE user_id = ?", (amount, member.id))
    db.commit()
    await interaction.response.send_message(f"✅ Added {amount} vouches to {member.mention}")

# Leaderboard & Remove Commands
@bot.tree.command(name="leaderboard", description="Top 10 generators")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT user_id, gens FROM users ORDER BY gens DESC LIMIT 10")
    rows = cursor.fetchall()
    lb = "\n".join([f"**{i+1}.** <@{r[0]}> — `{r[1]}`" for i, r in enumerate(rows)])
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Leaderboard", description=lb or "No data"))

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
                          
