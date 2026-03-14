import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
from flask import Flask
from threading import Thread

# --- 🌐 KEEP ALIVE SYSTEM (Render-এর জন্য) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ⚙️ CONFIGURATION ---
OWNER_ID = 1242372804859400195
TOKEN = os.environ.get('DISCORD_TOKEN')
PREMIUM_CHANNEL_ID = 1479080682616520718
PAID_CHANNEL_ID = 1479080682616520717
BASE_PATH = "categories/"
STAFF_IDS = [OWNER_ID]

if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

# --- 🗄️ DATABASE SETUP ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Bot is online and commands are synced!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def update_user(user_id, gen_inc=0, vouch_inc=0):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, gens, vouches) VALUES (?, 0, 0)", (user_id,))
    cursor.execute("UPDATE users SET gens = gens + ?, vouches = vouches + ? WHERE user_id = ?", (gen_inc, vouch_inc, user_id))
    db.commit()

def get_count(category):
    path = f"{BASE_PATH}{category.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return len([line for line in f.readlines() if line.strip()])
    return 0

def get_progress_bar(count):
    filled = min(int(count / 20 * 5), 5) 
    return "█" * filled + "░" * (5 - filled)

# --- 🚀 SLASH COMMANDS ---

@bot.tree.command(name="help", description="Show all available commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Commands — Gen Bot", description="All commands use `/`", color=discord.Color.default())
    embed.add_field(name="👥 Members", value="`/gen` `/profile` `/leaderboard` `/stock`", inline=False)
    embed.add_field(name="🛡️ Staff", value="`/add` `/send` `/remove` `/addv` ", inline=False)
    embed.add_field(name="🏷️ Tiers", value="🟢 free · 🟣 premium · 🟡 paid", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stock", description="Check current stock status")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Stock — All", color=discord.Color.default())
    sections = {
        "🟢 FREE": ["Bin", "Crunchyroll", "Disney", "Hbomax", "Hotmail", "Netflix", "Paramount", "Spotify", "Xbox"],
        "🟣 PREMIUM": ["Dazn", "Disney", "Netflix", "Steam"],
        "🟡 PAID": ["test2"]
    }
    total_all = 0
    for title, cats in sections.items():
        text = ""
        for cat in cats:
            c = get_count(cat)
            text += f"{get_progress_bar(c)} **{cat}** — {c} accounts\n"
            total_all += c
        embed.add_field(name=title, value=text or "Out of Stock", inline=False)
    embed.set_footer(text=f"Total: {total_all} accounts available")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gen", description="Generate an account")
async def gen(interaction: discord.Interaction, category: str):
    cat = category.lower()
    if "premium" in cat and interaction.channel_id != PREMIUM_CHANNEL_ID:
        return await interaction.response.send_message("❌ Use the **Premium** channel!", ephemeral=True)
    if "paid" in cat and interaction.channel_id != PAID_CHANNEL_ID:
        return await interaction.response.send_message("❌ Use the **Paid** channel!", ephemeral=True)

    path = f"{BASE_PATH}{category.capitalize()}.txt"
    if not os.path.exists(path) or get_count(category) == 0:
        return await interaction.response.send_message(f"⚠️ **{category.capitalize()}** is out of stock!", ephemeral=True)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    acc = lines.pop(0).strip()
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    try:
        await interaction.user.send(f"📦 **Your {category.capitalize()} Account:**\n`{acc}`")
        update_user(interaction.user.id, gen_inc=1)
        await interaction.response.send_message("✅ Check your DMs!", ephemeral=True)
    except:
        with open(path, "a", encoding="utf-8") as f:
            f.write(acc + "\n")
        await interaction.response.send_message("❌ DMs closed!", ephemeral=True)

@bot.tree.command(name="profile", description="Check stats")
async def profile(interaction: discord.Interaction):
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (interaction.user.id,))
    row = cursor.fetchone()
    gens, vouches = (row[0], row[1]) if row else (0, 0)
    embed = discord.Embed(title=f"👤 {interaction.user.name}'s Profile", color=discord.Color.blue())
    embed.add_field(name="Generated", value=f"📦 {gens}", inline=True)
    embed.add_field(name="Vouches", value=f"⭐ {vouches}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add", description="Add account (Staff)")
async def add(interaction: discord.Interaction, category: str, account: str):
    if interaction.user.id not in STAFF_IDS:
        return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    with open(f"{BASE_PATH}{category.capitalize()}.txt", "a", encoding="utf-8") as f:
        f.write(account + "\n")
    await interaction.response.send_message(f"✅ Added to **{category.capitalize()}**.")

# --- 🚀 BOT RUN ---
if __name__ == "__main__":
    keep_alive() # সার্ভার চালু করবে যাতে Render বন্ধ না করে
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ TOKEN NOT FOUND!")
                         
