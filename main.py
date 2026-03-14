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
        print(f"🚀 Raizen Bot Linked!")

bot = MyBot()

# --- 🛠️ HELPERS ---
def get_count(service):
    path = f"{BASE_PATH}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    return 0

# --- 🚀 COMMANDS ---

@bot.tree.command(name="gen", description="Generate a ticket for an account")
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
        return await interaction.response.send_message(f"⚠️ **{service_name}** out of stock!", ephemeral=True)

    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)

    t_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cursor.execute("INSERT INTO tickets (code, service, account, tier) VALUES (?, ?, ?, ?)", (t_code, service_name, acc, tier.name))
    db.commit()

    # আপনার রিকোয়েস্ট অনুযায়ী: টিকিট কোডের নিচে সার্ভিসের নাম থাকবে
    embed = discord.Embed(title="🎫 Ticket Generated", color=0x00FF00)
    embed.add_field(name="Ticket Code:", value=f"**{t_code}**", inline=False)
    embed.add_field(name="Service:", value=f"**{service_name}**", inline=False)
    embed.set_footer(text="Use /redeem to claim your account!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="add", description="Add stock (Any service name works)")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    if interaction.user.id not in STAFF_IDS: return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    try:
        content = await file.read()
        lines = content.decode("utf-8").splitlines()
        valid = [l for l in lines if l.strip()]
        
        path = f"{BASE_PATH}/{service.capitalize()}.txt"
        with open(path, "a", encoding="utf-8") as f:
            for acc in valid: f.write(acc + "\n")
        
        await interaction.followup.send(f"✅ Added `{len(valid)}` accounts to **{service.capitalize()}** ({tier.name})")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="stock", description="Check all available stock")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Live Stock Status", color=0xFFFFFF)
    
    # ফোল্ডারে থাকা সব .txt ফাইল অটোমেটিক রিড করবে
    files = [f for f in os.listdir(BASE_PATH) if f.endswith('.txt')]
    if not files:
        return await interaction.response.send_message("Stock is empty!", ephemeral=True)
    
    stock_list = ""
    for f_name in files:
        name = f_name.replace(".txt", "")
        count = get_count(name)
        stock_list += f"░░░░░ **{name}** — {count} accounts\n"
    
    embed.description = stock_list
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="redeem", description="Claim your account")
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
            await interaction.user.send(f"🎁 **Claimed!**\nService: **{service}**\nTier: **{tier}**\nAccount: `{account}`")
            await interaction.response.send_message(f"✅ Code Valid! Service: **{service}**. Check DMs!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ DM Closed! I couldn't send the account.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid or Expired Code!", ephemeral=True)

@bot.tree.command(name="profile", description="Check stats")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (target.id,))
    row = cursor.fetchone()
    gens, vouches = (row[0], row[1]) if row else (0, 0)
    await interaction.response.send_message(f"👤 **{target.name}**\n📦 Gens: `{gens}`\n⭐ Vouches: `{vouches}`")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
        
