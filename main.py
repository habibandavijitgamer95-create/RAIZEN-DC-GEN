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
LOG_CH = 1479239531499880628 
STAFF_IDS = [1242372804859400195, 1406599824089808967, 1040256699480686604]
BASE_PATH = "categories/"

# এরর ফিক্সিং ফোল্ডার চেক
if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH, exist_ok=True)

# --- 🗄️ DATABASE SETUP ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, reward TEXT)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Raizen Gen Bot Linked & Synced!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def get_count(service):
    path = os.path.join(BASE_PATH, f"{service.capitalize()}.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return len([l for l in f.readlines() if l.strip()])
    return 0

# --- 🚀 MEMBER COMMANDS ---

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
        "`/redeem` — Validate a ticket/code\n"
        "`/add` — Add accounts (attach .txt)\n"
        "`/send` — Send accounts via DM\n"
        "`/remove` — Remove stock\n"
        "`/addv` — Manually add vouches"
    ), inline=False)
    embed.add_field(name="🏷️ Available Tiers", value="🟢 free · 🟣 premium · 🟡 paid", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gen", description="Generate an account")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    # স্ট্যাফরা সব চ্যানেলে পারবে, ইউজাররা শুধু নির্দিষ্ট চ্যানেলে
    if interaction.user.id not in STAFF_IDS:
        if tier.value == "free" and interaction.channel_id != FREE_CH:
            return await interaction.response.send_message(f"❌ Use <#{FREE_CH}> for Free!", ephemeral=True)
        if tier.value == "premium" and interaction.channel_id != PREMIUM_CH:
            return await interaction.response.send_message(f"❌ Use <#{PREMIUM_CH}> for Premium!", ephemeral=True)
        if tier.value == "paid" and interaction.channel_id != PAID_CH:
            return await interaction.response.send_message(f"❌ Use <#{PAID_CH}> for Paid!", ephemeral=True)

    service_name = service.capitalize()
    path = os.path.join(BASE_PATH, f"{service_name}.txt")

    if not os.path.exists(path) or get_count(service_name) == 0:
        return await interaction.response.send_message(f"⚠️ **{service_name}** out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    try:
        await interaction.user.send(f"📦 **Your {service_name} ({tier.name}) Account:**\n`{acc}`")
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        cursor.execute("UPDATE users SET gens = gens + 1 WHERE user_id = ?", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Sent to DMs!", ephemeral=True)

        # Log Notification
        log_ch = bot.get_channel(LOG_CH)
        if log_ch:
            embed = discord.Embed(title="🚀 New Gen Log", color=0x00FF00)
            embed.add_field(name="User", value=f"{interaction.user.mention}")
            embed.add_field(name="Service", value=service_name)
            embed.add_field(name="Tier", value=tier.name)
            await log_ch.send(embed=embed)
    except:
        with open(path, "a") as f: f.write(acc + "\n")
        await interaction.response.send_message("❌ DM Closed! Stock returned.", ephemeral=True)

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
            c = get_count(cat); total += c
            text += f"░░░░░ **{cat}** — {c} accounts\n"
        embed.add_field(name=title, value=text, inline=False)
    embed.set_footer(text=f"Total: {total} accounts available")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="Check your stats")
async def profile(interaction: discord.Interaction):
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (interaction.user.id,))
    row = cursor.fetchone()
    gens, vouches = (row[0], row[1]) if row else (0, 0)
    await interaction.response.send_message(f"👤 **{interaction.user.name}**\n📦 Generated: `{gens}`\n⭐ Vouches: `{vouches}`")

# --- 🛡️ STAFF COMMANDS ---

@bot.tree.command(name="add", description="Add accounts via .txt file")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    content = await file.read()
    with open(os.path.join(BASE_PATH, f"{service.capitalize()}.txt"), "a", encoding="utf-8") as f:
        f.write(content.decode("utf-8") + "\n")
    await interaction.response.send_message(f"✅ Added to **{service.capitalize()}** ({tier.name})")

@bot.tree.command(name="remove", description="Remove amount from stock")
async def remove(interaction: discord.Interaction, service: str, amount: int):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    path = os.path.join(BASE_PATH, f"{service.capitalize()}.txt")
    if os.path.exists(path):
        with open(path, "r") as f: lines = f.readlines()
        new_lines = lines[amount:]
        with open(path, "w") as f: f.writelines(new_lines)
        await interaction.response.send_message(f"🗑️ Removed {amount} from {service.capitalize()}.")
    else: await interaction.response.send_message("❌ Not found!")

@bot.tree.command(name="addv", description="Add vouches to member")
async def addv(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,))
    cursor.execute("UPDATE users SET vouches = vouches + ? WHERE user_id = ?", (amount, member.id))
    db.commit()
    await interaction.response.send_message(f"⭐ Added {amount} vouches to {member.mention}!")

@bot.tree.command(name="redeem", description="Redeem a reward code")
async def redeem(interaction: discord.Interaction, code: str):
    cursor.execute("SELECT reward FROM redeem_codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        reward = row[0]
        cursor.execute("DELETE FROM redeem_codes WHERE code = ?", (code,))
        db.commit()
        await interaction.response.send_message(f"🎉 Success! You redeemed: **{reward}**")
    else: await interaction.response.send_message("❌ Invalid code!", ephemeral=True)

@bot.tree.command(name="create_code", description="Create a redeem code (Staff)")
async def create_code(interaction: discord.Interaction, code: str, reward: str):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    cursor.execute("INSERT INTO redeem_codes (code, reward) VALUES (?, ?)", (code, reward))
    db.commit()
    await interaction.response.send_message(f"✅ Created code: `{code}` with reward: `{reward}`")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
        
