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
        print(f"🚀 Bot Synchronized - 100% Anti-Timeout Active")

bot = MyBot()

# --- 🛠️ HELPER ---
def get_count(service):
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    return 0

# --- 🚀 ALL COMMANDS ---

# ১. GEN COMMAND
@bot.tree.command(name="gen", description="Generate a ticket code")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    await interaction.response.defer(ephemeral=True) # <-- Time-out Fix
    
    if interaction.user.id not in STAFF_IDS:
        ch_map = {"free": FREE_CH, "premium": PREMIUM_CH, "paid": PAID_CH}
        if interaction.channel_id != ch_map.get(tier.value):
            return await interaction.followup.send(f"❌ Use <#{ch_map.get(tier.value)}>", ephemeral=True)

    service_name = service.capitalize()
    path = f"{BASE_PATH}/{service_name}.txt"
    if get_count(service_name) == 0:
        return await interaction.followup.send(f"⚠️ {service_name} out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    t_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cursor.execute("INSERT INTO tickets (code, service, account, tier) VALUES (?, ?, ?, ?)", (t_code, service_name, acc, tier.name))
    db.commit()

    embed = discord.Embed(title="🎫 Ticket Created", color=0x00FF00)
    embed.add_field(name="Code:", value=f"**{t_code}**", inline=True)
    embed.add_field(name="Service:", value=f"**{service_name}**", inline=True)
    await interaction.followup.send(embed=embed, ephemeral=True)

# ২. REDEEM COMMAND
@bot.tree.command(name="redeem", description="Claim account via code")
async def redeem(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True) # <-- Time-out Fix
    
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
            await interaction.user.send(f"🎁 **Claimed!**\nService: **{service}**\nAccount: `{account}`")
            await interaction.followup.send(f"✅ Success! It was **{service}**. Check DM!", ephemeral=True)
        except: await interaction.followup.send("❌ DM Closed! Could not send account.", ephemeral=True)
    else: await interaction.followup.send("❌ Invalid Code!", ephemeral=True)

# ৩. STOCK COMMAND
@bot.tree.command(name="stock", description="Check available accounts")
async def stock(interaction: discord.Interaction):
    await interaction.response.defer() # <-- Time-out Fix (No more "did not respond")
    
    embed = discord.Embed(title="📦 Stock Status", color=0xFFFFFF)
    files = [f for f in os.listdir(BASE_PATH) if f.endswith('.txt')]
    desc = ""
    for f in files:
        name = f.replace(".txt", "")
        count = get_count(name)
        if count > 0:
            desc += f"░░░░░ **{name}** — {count}\n"
    
    embed.description = desc or "Stock is empty!"
    await interaction.followup.send(embed=embed)

# ৪. PROFILE COMMAND
@bot.tree.command(name="profile", description="Check stats")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer() # <-- Time-out Fix
    
    target = member or interaction.user
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (target.id,))
    row = cursor.fetchone()
    g, v = (row[0], row[1]) if row else (0, 0)
    await interaction.followup.send(f"👤 **{target.name}**\n📦 Gens: `{g}` | ⭐ Vouches: `{v}`")

# ৫. LEADERBOARD COMMAND
@bot.tree.command(name="leaderboard", description="Top 10 users")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer() # <-- Time-out Fix
    
    cursor.execute("SELECT user_id, gens FROM users ORDER BY gens DESC LIMIT 10")
    rows = cursor.fetchall()
    lb = "\n".join([f"**{i+1}.** <@{r[0]}> — `{r[1]}`" for i, r in enumerate(rows)])
    await interaction.followup.send(embed=discord.Embed(title="🏆 Leaderboard", description=lb or "No data"))

# ৬. ADD COMMAND
@bot.tree.command(name="add", description="Add stock via file")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    await interaction.response.defer(ephemeral=True) # <-- Time-out Fix
    
    if interaction.user.id not in STAFF_IDS: 
        return await interaction.followup.send("❌ Staff only!")
    
    content = await file.read()
    valid = [l for l in content.decode("utf-8").splitlines() if l.strip()]
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    with open(path, "a", encoding="utf-8") as f:
        for line in valid: f.write(line + "\n")
    await interaction.followup.send(f"✅ Added {len(valid)} accounts to **{service.capitalize()}**")

# ৭. ADDV COMMAND
@bot.tree.command(name="addv", description="Add vouches to user")
async def addv(interaction: discord.Interaction, member: discord.Member, amount: int):
    await interaction.response.defer() # <-- Time-out Fix
    
    if interaction.user.id not in STAFF_IDS: 
        return await interaction.followup.send("❌ Staff only!")
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,))
    cursor.execute("UPDATE users SET vouches = vouches + ? WHERE user_id = ?", (amount, member.id))
    db.commit()
    await interaction.followup.send(f"✅ Added {amount} vouches to {member.mention}")

# ৮. SEND COMMAND
@bot.tree.command(name="send", description="Send account directly")
async def send(interaction: discord.Interaction, member: discord.Member, service: str):
    await interaction.response.defer(ephemeral=True) # <-- Time-out Fix
    
    if interaction.user.id not in STAFF_IDS: 
        return await interaction.followup.send("❌ Staff only!")
        
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    if get_count(service) > 0:
        with open(path, "r") as f: lines = f.readlines()
        acc = lines.pop(0).strip()
        with open(path, "w") as f: f.writelines(lines)
        try:
            await member.send(f"🎁 Gift: `{acc}` from {service}")
            await interaction.followup.send(f"✅ Sent to {member.mention}")
        except:
            await interaction.followup.send("❌ DM is closed!")
    else:
        await interaction.followup.send("⚠️ Out of stock!")

# ৯. REMOVE COMMAND
@bot.tree.command(name="remove", description="Remove stock amount")
async def remove(interaction: discord.Interaction, service: str, amount: int):
    await interaction.response.defer(ephemeral=True) # <-- Time-out Fix
    
    if interaction.user.id not in STAFF_IDS: 
        return await interaction.followup.send("❌ Staff only!")
        
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r") as f: lines = f.readlines()
        with open(path, "w") as f: f.writelines(lines[amount:])
        await interaction.followup.send(f"🗑️ Removed {amount} from {service}")
    else:
        await interaction.followup.send("⚠️ Service not found!")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
              
