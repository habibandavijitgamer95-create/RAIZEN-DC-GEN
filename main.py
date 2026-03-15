import discord
from discord import app_commands
from discord.ext import commands
import os, sqlite3, random, string
from flask import Flask
from threading import Thread
from datetime import datetime

# --- 🌐 KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- ⚙️ CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
STAFF_IDS = [1242372804859400195, 1406599824089808967, 1040256699480686604]
BASE_PATH = "categories"

# Tier based sub-folders
TIERS = ["free", "premium", "paid"]
for t in TIERS:
    os.makedirs(f"{BASE_PATH}/{t}", exist_ok=True)

# --- 🗄️ DATABASE ---
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS tickets (code TEXT PRIMARY KEY, service TEXT, account TEXT, tier TEXT)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- 🛠️ HELPER ---
def get_stock_count(tier, service):
    path = f"{BASE_PATH}/{tier}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    return 0

# --- 🚀 COMMANDS ---

@bot.tree.command(name="stock", description="View available stock by tiers")
async def stock(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="📦 Stock — All", color=0x2f3136)
    total_accs = 0
    
    tier_emojis = {"free": "🟢 FREE", "premium": "🟣 PREMIUM", "paid": "🟡 PAID"}
    
    for tier in TIERS:
        files = [f for f in os.listdir(f"{BASE_PATH}/{tier}") if f.endswith('.txt')]
        if not files:
            continue
            
        desc = ""
        for f in files:
            name = f.replace(".txt", "")
            count = get_stock_count(tier, name)
            total_accs += count
            if count >= 0:
                desc += f"░░░░░ **{name}** — {count} accounts\n"
        
        if desc:
            embed.add_field(name=tier_emojis[tier], value=desc, inline=False)

    now = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    embed.set_footer(text=f"Total: {total_accs} accounts available | {now}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="gen", description="Generate an account ticket")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    await interaction.response.defer(ephemeral=True)
    
    service_name = service.capitalize()
    path = f"{BASE_PATH}/{tier.value}/{service_name}.txt"
    
    if get_stock_count(tier.value, service_name) == 0:
        return await interaction.followup.send(f"⚠️ {service_name} in {tier.name} is out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    t_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cursor.execute("INSERT INTO tickets (code, service, account, tier) VALUES (?, ?, ?, ?)", (t_code, service_name, acc, tier.name))
    db.commit()

    # সুন্দর টিকিট এমবেড
    embed = discord.Embed(title="🎫 Ticket Created", color=0x5865F2)
    embed.description = f"Your ticket for **{service_name}** has been generated."
    embed.add_field(name="Ticket Code", value=f"```\n{t_code}\n```", inline=False)
    embed.add_field(name="How to use?", value=f"Use `/redeem code:{t_code}` to claim your account.", inline=False)
    embed.set_footer(text="Keep this code private!")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="add", description="Add accounts to a specific tier")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in STAFF_IDS: return await interaction.followup.send("❌ No permission.")
    
    content = await file.read()
    valid = [l for l in content.decode("utf-8").splitlines() if l.strip()]
    path = f"{BASE_PATH}/{tier.value}/{service.capitalize()}.txt"
    
    with open(path, "a", encoding="utf-8") as f:
        for line in valid: f.write(line + "\n")
    await interaction.followup.send(f"✅ Added {len(valid)} accounts to {tier.name} -> {service.capitalize()}")

# --- বাকি কমান্ডগুলো (Redeem, Profile, etc.) একই থাকবে ---
# [Note: আগের দেওয়া কোড থেকে Redeem, Profile, Leaderboard, Addv, Send, Remove কমান্ডগুলো এখানে যোগ করে নিন]

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
    
