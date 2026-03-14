import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import random
import string
from flask import Flask
from threading import Thread

# --- 🌐 KEEP ALIVE (For Render) ---
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

# ✅ RENDER ERROR FIX: exist_ok=True ensures no crash if folder exists
if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH, exist_ok=True)

# --- 🗄️ DATABASE ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS tickets (code TEXT PRIMARY KEY, service TEXT, account TEXT, tier TEXT)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Raizen Ticket System Online!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def generate_ticket_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

def get_count(service):
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return len([l for l in f.readlines() if l.strip()])
    return 0

# --- 🚀 COMMANDS ---

@bot.tree.command(name="help", description="Show all commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Commands — Gen Bot", color=0xFFFFFF)
    embed.add_field(name="👤 Members", value="`/gen` · `/redeem` · `/profile` · `/stock` · `/leaderboard` ", inline=False)
    embed.add_field(name="🛡️ Staff", value="`/add` · `/addv` · `/remove` · `/send` ", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gen", description="Generate a 4-digit ticket code")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    if interaction.user.id not in STAFF_IDS:
        if tier.value == "free" and interaction.channel_id != FREE_CH:
            return await interaction.response.send_message(f"❌ Use <#{FREE_CH}>", ephemeral=True)
        if tier.value == "premium" and interaction.channel_id != PREMIUM_CH:
            return await interaction.response.send_message(f"❌ Use <#{PREMIUM_CH}>", ephemeral=True)
        if tier.value == "paid" and interaction.channel_id != PAID_CH:
            return await interaction.response.send_message(f"❌ Use <#{PAID_CH}>", ephemeral=True)

    service_name = service.capitalize()
    path = f"{BASE_PATH}/{service_name}.txt"

    if not os.path.exists(path) or get_count(service_name) == 0:
        return await interaction.response.send_message(f"⚠️ **{service_name}** out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    account_data = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    t_code = generate_ticket_code()
    cursor.execute("INSERT INTO tickets (code, service, account, tier) VALUES (?, ?, ?, ?)", 
                   (t_code, service_name, account_data, tier.name))
    db.commit()

    await interaction.response.send_message(f"🎫 Your ticket code: **{t_code}**\nUse `/redeem` to get the account!", ephemeral=True)

@bot.tree.command(name="redeem", description="Claim account using ticket code")
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
            await interaction.user.send(f"🎁 **Redeemed!**\nService: {service}\nTier: {tier}\nAccount: `{account}`")
            await interaction.response.send_message(f"✅ Valid! Category: **{tier}**, Service: **{service}**. Check DMs!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ DM Closed!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid Code!", ephemeral=True)

@bot.tree.command(name="add", description="Add stock via file")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("Staff only!", ephemeral=True)
    content = await file.read()
    with open(f"{BASE_PATH}/{service.capitalize()}.txt", "a", encoding="utf-8") as f:
        f.write(content.decode("utf-8") + "\n")
    await interaction.response.send_message(f"✅ Added to **{service.capitalize()}** ({tier.name})")

@bot.tree.command(name="stock", description="Check stock")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Stock Status", color=0xFFFFFF)
    sections = {"🟢 FREE": ["Xbox", "Netflix", "Spotify"], "🟣 PREMIUM": ["Steam", "Netflix"], "🟡 PAID": ["test2"]}
    for title, cats in sections.items():
        text = ""
        for cat in cats: text += f"░░░░░ **{cat}** — {get_count(cat)}\n"
        embed.add_field(name=title, value=text, inline=False)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
            
