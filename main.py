import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import random
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
STAFF_IDS = [OWNER_ID]

# --- 🗄️ DATABASE SETUP ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY, reward TEXT)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Bot is online and slash commands are synced!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def update_user(user_id, gen_inc=0, vouch_inc=0):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, gens, vouches) VALUES (?, 0, 0)", (user_id,))
    cursor.execute("UPDATE users SET gens = gens + ?, vouches = vouches + ? WHERE user_id = ?", (gen_inc, vouch_inc, user_id))
    db.commit()

def get_count(category):
    path = f"{category.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return len([line for line in f.readlines() if line.strip()])
    return 0

def get_progress_bar(count):
    filled = min(int(count / 20 * 5), 5) 
    return "█" * filled + "░" * (5 - filled)

# --- 🚀 SLASH COMMANDS ---

# 1. Help Command
@bot.tree.command(name="help", description="Show all commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="User", value="`/gen`, `/stock`, `/profile`, `/leaderboard`, `/redeem`", inline=False)
    embed.add_field(name="Staff", value="`/add`, `/send`, `/addv`", inline=False)
    await interaction.response.send_message(embed=embed)

# 2. Stock Command
@bot.tree.command(name="stock", description="Check current stock")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Current Stock", color=discord.Color.green())
    # আপনি আপনার টেক্সট ফাইলের নাম অনুযায়ী এই লিস্ট আপডেট করতে পারেন
    categories = ["Steam", "Netflix", "Disney", "Spotify", "Crunchyroll"] 
    for cat in categories:
        count = get_count(cat)
        embed.add_field(name=f"{cat}", value=f"{get_progress_bar(count)} ({count})", inline=True)
    await interaction.response.send_message(embed=embed)

# 3. Gen Command
@bot.tree.command(name="gen", description="Generate an account")
async def gen(interaction: discord.Interaction, category: str):
    cat = category.lower()
    if "premium" in cat and interaction.channel_id != PREMIUM_CHANNEL_ID:
        return await interaction.response.send_message("❌ Use the Premium channel!", ephemeral=True)
    
    path = f"{category.capitalize()}.txt"
    if not os.path.exists(path) or get_count(category) == 0:
        return await interaction.response.send_message(f"⚠️ {category.capitalize()} is out of stock!", ephemeral=True)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    acc = lines.pop(0).strip()
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    try:
        await interaction.user.send(f"📦 **Your {category.capitalize()} Account:**\n`{acc}`")
        update_user(interaction.user.id, gen_inc=1)
        await interaction.response.send_message("✅ Sent to DM!", ephemeral=True)
    except:
        with open(path, "a", encoding="utf-8") as f: f.write(acc + "\n")
        await interaction.response.send_message("❌ DM closed!", ephemeral=True)

# 4. Profile Command
@bot.tree.command(name="profile", description="Check your stats")
async def profile(interaction: discord.Interaction):
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (interaction.user.id,))
    row = cursor.fetchone()
    gens, vouches = (row[0], row[1]) if row else (0, 0)
    embed = discord.Embed(title=f"👤 {interaction.user.name}'s Profile", color=discord.Color.gold())
    embed.add_field(name="Gens", value=f"📦 {gens}", inline=True)
    embed.add_field(name="Vouches", value=f"⭐ {vouches}", inline=True)
    await interaction.response.send_message(embed=embed)

# 5. Leaderboard Command
@bot.tree.command(name="leaderboard", description="Top 10 generators")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT user_id, gens FROM users ORDER BY gens DESC LIMIT 10")
    rows = cursor.fetchall()
    text = ""
    for i, (uid, g) in enumerate(rows, 1):
        text += f"**#{i}** <@{uid}> — `{g}` gens\n"
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Top 10 Generators", description=text or "No data", color=0xFFD700))

# 6. Send Command (Staff)
@bot.tree.command(name="send", description="Send account to user (Staff)")
async def send_acc(interaction: discord.Interaction, user: discord.Member, category: str):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("Staff only!", ephemeral=True)
    path = f"{category.capitalize()}.txt"
    if not os.path.exists(path) or get_count(category) == 0: return await interaction.response.send_message("Out of stock!")
    
    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)
    try:
        await user.send(f"🎁 Gift from Staff: `{acc}`")
        await interaction.response.send_message(f"✅ Sent to {user.mention}")
    except: await interaction.response.send_message("User DM closed!")

# 7. Add Vouch (Staff)
@bot.tree.command(name="addv", description="Add vouch to user (Staff)")
async def addv(interaction: discord.Interaction, user: discord.Member):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("Staff only!", ephemeral=True)
    update_user(user.id, vouch_inc=1)
    await interaction.response.send_message(f"⭐ Vouch added to {user.mention}!")

# 8. Redeem Command
@bot.tree.command(name="redeem", description="Redeem a code")
async def redeem(interaction: discord.Interaction, code: str):
    cursor.execute("SELECT reward FROM codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        reward = row[0]
        cursor.execute("DELETE FROM codes WHERE code = ?", (code,))
        db.commit()
        await interaction.response.send_message(f"🎉 Redeemed: **{reward}**")
    else:
        await interaction.response.send_message("❌ Invalid code!", ephemeral=True)

# --- 🚀 RUN BOT ---
if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN not found!")
        
