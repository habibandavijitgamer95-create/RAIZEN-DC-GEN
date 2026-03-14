import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
from flask import Flask
from threading import Thread

# --- 🌐 KEEP ALIVE SYSTEM ---
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
LOG_CH = 1479239531499880628 # আপনার দেওয়া নতুন লগ চ্যানেল আইডি
STAFF_IDS = [1242372804859400195, 1406599824089808967, 1040256699480686604]
BASE_PATH = "categories/"

if not os.path.exists(BASE_PATH): os.makedirs(BASE_PATH)

# --- 🗄️ DATABASE ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Raizen Gen Bot Linked!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def get_count(service):
    path = f"{BASE_PATH}{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return len([l for l in f.readlines() if l.strip()])
    return 0

# --- 🚀 SLASH COMMANDS ---

# ১. /help (স্ক্রিনশটের মতো হুবহু সাজানো)
@bot.tree.command(name="help", description="Show all available commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Commands — Gen Bot", color=0xFFFFFF)
    embed.description = "All commands use `/`"
    
    embed.add_field(name="👤 Members", value=(
        "`/gen` — Generate an account\n"
        "`/profile` — View profile & stats\n"
        "`/promote` — View vouch progress\n"
        "`/leaderboard` — Top 10 generators\n"
        "`/stock` — View available stock"
    ), inline=False)
    
    embed.add_field(name="🛡️ Staff", value=(
        "`/redeem` — Validate a ticket\n"
        "`/add` — Add accounts (attach .txt)\n"
        "`/send` — Send accounts via DM\n"
        "`/remove` — Remove stock\n"
        "`/addv` — Manually add vouches"
    ), inline=False)
    
    embed.add_field(name="🏷️ Available Tiers", value="🟢 free · 🟣 premium · 🟡 paid", inline=False)
    await interaction.response.send_message(embed=embed)

# ২. /gen (Tier & Service + Channel Check + Logs)
@bot.tree.command(name="gen", description="Generate an account")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    if interaction.user.id not in STAFF_IDS:
        if tier.value == "free" and interaction.channel_id != FREE_CH:
            return await interaction.response.send_message(f"❌ Use <#{FREE_CH}> for Free!", ephemeral=True)
        if tier.value == "premium" and interaction.channel_id != PREMIUM_CH:
            return await interaction.response.send_message(f"❌ Use <#{PREMIUM_CH}> for Premium!", ephemeral=True)
        if tier.value == "paid" and interaction.channel_id != PAID_CH:
            return await interaction.response.send_message(f"❌ Use <#{PAID_CH}> for Paid!", ephemeral=True)

    service_name = service.capitalize()
    path = f"{BASE_PATH}{service_name}.txt"

    if not os.path.exists(path) or get_count(service_name) == 0:
        return await interaction.response.send_message(f"⚠️ **{service_name}** is out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    try:
        await interaction.user.send(f"📦 **Your {service_name} ({tier.name}) Account:**\n`{acc}`")
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        cursor.execute("UPDATE users SET gens = gens + 1 WHERE user_id = ?", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Your **{service_name}** account sent to DMs!", ephemeral=True)

        # Log Channel
        log_ch = bot.get_channel(LOG_CH)
        if log_ch:
            log_embed = discord.Embed(title="🚀 New Gen Log", color=0x00FF00)
            log_embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
            log_embed.add_field(name="Service", value=service_name)
            log_embed.add_field(name="Tier", value=tier.name)
            await log_ch.send(embed=log_embed)
    except:
        with open(path, "a") as f: f.write(acc + "\n")
        await interaction.response.send_message("❌ DM Closed! Account returned to stock.", ephemeral=True)

# ৩. /add (Staff Only - .txt ফাইল দিয়ে স্টক বাড়ানো)
@bot.tree.command(name="add", description="Add accounts via .txt file")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    if not file.filename.endswith(".txt"): return await interaction.response.send_message("❌ Upload a .txt file!", ephemeral=True)
    
    content = await file.read()
    accounts = content.decode("utf-8")
    
    with open(f"{BASE_PATH}{service.capitalize()}.txt", "a", encoding="utf-8") as f:
        f.write(accounts + "\n")
    
    await interaction.response.send_message(f"✅ Accounts added to **{service.capitalize()}** ({tier.name})")

# ৪. /remove (Staff Only - স্টক কমানো)
@bot.tree.command(name="remove", description="Remove amount from stock")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def remove(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, amount: int):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    path = f"{BASE_PATH}{service.capitalize()}.txt"
    if not os.path.exists(path): return await interaction.response.send_message("Category not found!", ephemeral=True)
    
    with open(path, "r") as f: lines = f.readlines()
    if len(lines) < amount: amount = len(lines)
    for _ in range(amount): lines.pop(0)
    with open(path, "w") as f: f.writelines(lines)
    
    await interaction.response.send_message(f"🗑️ Removed `{amount}` accounts from **{service.capitalize()}**.")

# ৫. /stock (স্ক্রিনশটের মতো প্রফেশনাল স্টাইল)
@bot.tree.command(name="stock", description="Check stock status")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Stock — All", color=0xFFFFFF)
    sections = {
        "🟢 FREE": ["Bin", "Crunchyroll", "Disney", "Hbomax", "Hotmail", "Netflix", "Paramount", "Spotify", "Xbox"],
        "🟣 PREMIUM": ["Dazn", "Disney", "Netflix", "Steam"],
        "🟡 PAID": ["test2"]
    }
    total = 0
    for title, cats in sections.items():
        text = ""
        for cat in cats:
            count = get_count(cat)
            total += count
            text += f"░░░░░ **{cat}** — {count} accounts\n"
        embed.add_field(name=title, value=text, inline=False)
    embed.set_footer(text=f"Total: {total} accounts available")
    await interaction.response.send_message(embed=embed)

# ৬. /send (মেম্বারকে মেনশন করে অ্যাকাউন্ট পাঠানো)
@bot.tree.command(name="send", description="Send account to member")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def send_member(interaction: discord.Interaction, member: discord.Member, tier: app_commands.Choice[str], service: str):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    service_name = service.capitalize()
    path = f"{BASE_PATH}{service_name}.txt"
    if not os.path.exists(path) or get_count(service_name) == 0: return await interaction.response.send_message("Stock out!", ephemeral=True)
    
    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, f"w") as f: f.writelines(lines)
    try:
        await member.send(f"🎁 **Staff Gift!**\nService: {service_name}\nTier: {tier.name}\nAccount: `{acc}`")
        await interaction.response.send_message(f"✅ Sent to {member.mention}")
    except: await interaction.response.send_message("User DM closed!")

# ৭. /addv (ভাউচ অ্যাড করা)
@bot.tree.command(name="addv", description="Add vouches")
async def addv(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,))
    cursor.execute("UPDATE users SET vouches = vouches + ? WHERE user_id = ?", (amount, member.id))
    db.commit()
    await interaction.response.send_message(f"⭐ Added {amount} vouches to {member.mention}!")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
    
