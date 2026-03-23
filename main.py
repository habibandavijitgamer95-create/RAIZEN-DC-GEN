import discord
from discord import app_commands
from discord.ext import commands
import os, sqlite3, random, string
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
STAFF_IDS = [1242372804859400195, 1406599824089808967, 1040256699480686604]
BASE_PATH = "categories"

# Define the 5 Tiers
TIERS = ["free", "premium", "paid", "booster", "extreme"]
TIER_EMOJIS = {
    "free": "🟢 FREE",
    "premium": "🟣 PREMIUM",
    "paid": "🟡 PAID",
    "booster": "🚀 BOOSTER",
    "extreme": "🔥 EXTREME"
}

# Ensure directories exist for all tiers
for t in TIERS:
    os.makedirs(f"{BASE_PATH}/{t}", exist_ok=True)

# --- DATABASE SETUP ---
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, gens INTEGER DEFAULT 0, vouches INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS tickets (code TEXT PRIMARY KEY, service TEXT, account TEXT, tier TEXT)")
db.commit()

class RaizenBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Raizen Bot Online - All 10 Commands Synced!")

bot = RaizenBot()

# --- HELPER FUNCTIONS ---
def get_stock_count(tier, service):
    path = f"{BASE_PATH}/{tier}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    return 0

# --- BOT COMMANDS ---

@bot.tree.command(name="help", description="Show all available commands")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="📜 Raizen Gen Bot Commands", color=0xFFFFFF)
    embed.add_field(name="👤 Members", value="`/gen`, `/redeem`, `/stock`, `/profile`, `/leaderboard`, `/help`", inline=False)
    embed.add_field(name="🛡️ Staff", value="`/add`, `/send`, `/remove`, `/addv`", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="stock", description="View stock sorted by tiers")
async def stock(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="📦 Live Stock Status", color=0x2b2d31)
    total_accs = 0
    
    for tier in TIERS:
        files = [f for f in os.listdir(f"{BASE_PATH}/{tier}") if f.endswith('.txt')]
        desc = ""
        for f in files:
            name = f.replace(".txt", "")
            count = get_stock_count(tier, name)
            total_accs += count
            if count >= 0:
                desc += f"░░░░░ **{name}** — {count} accounts\n"
        if desc:
            embed.add_field(name=TIER_EMOJIS[tier], value=desc, inline=False)
    
    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    embed.set_footer(text=f"Total: {total_accs} accounts | Updated: {now}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="gen", description="Generate an account ticket")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid"),
    app_commands.Choice(name="🚀 booster", value="booster"),
    app_commands.Choice(name="🔥 extreme", value="extreme")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str):
    await interaction.response.defer(ephemeral=True)
    service_name = service.capitalize()
    path = f"{BASE_PATH}/{tier.value}/{service_name}.txt"
    
    if get_stock_count(tier.value, service_name) == 0:
        return await interaction.followup.send(f"⚠️ {service_name} is out of stock in {tier.name}!", ephemeral=True)
    
    with open(path, "r") as f: lines = f.readlines()
    acc = lines.pop(0).strip()
    with open(path, "w") as f: f.writelines(lines)
    
    t_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cursor.execute("INSERT INTO tickets (code, service, account, tier) VALUES (?, ?, ?, ?)", (t_code, service_name, acc, tier.name))
    db.commit()
    
    embed = discord.Embed(title="🎫 Ticket Generated", color=0x5865F2)
    embed.add_field(name="Ticket Code:", value=f"```\n{t_code}\n```", inline=False)
    embed.add_field(name="Instruction:", value=f"Use `/redeem code:{t_code}` to get your account.", inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="redeem", description="Claim your account using the ticket code")
async def redeem(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)
    cursor.execute("SELECT service, account FROM tickets WHERE code = ?", (code.upper(),))
    row = cursor.fetchone()
    if row:
        service, account = row
        cursor.execute("DELETE FROM tickets WHERE code = ?", (code.upper(),))
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        cursor.execute("UPDATE users SET gens = gens + 1 WHERE user_id = ?", (interaction.user.id,))
        db.commit()
        try:
            await interaction.user.send(f"🎁 **Account Claimed!**\nService: **{service}**\nAccount: `{account}`")
            await interaction.followup.send("✅ Success! Check your DM.", ephemeral=True)
        except:
            await interaction.followup.send("❌ Error: I cannot DM you. Please open your DMs.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Error: Invalid or expired ticket code.", ephemeral=True)

@bot.tree.command(name="profile", description="Check member stats")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT gens, vouches FROM users WHERE user_id = ?", (target.id,))
    row = cursor.fetchone()
    g, v = (row[0], row[1]) if row else (0, 0)
    embed = discord.Embed(title=f"👤 Profile: {target.name}", color=0x00FF00)
    embed.add_field(name="Gens", value=f"`{g}`", inline=True)
    embed.add_field(name="Vouches", value=f"`{v}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add", description="Add stock to a specific tier")
@app_commands.choices(tier=[
    app_commands.Choice(name="🟢 free", value="free"),
    app_commands.Choice(name="🟣 premium", value="premium"),
    app_commands.Choice(name="🟡 paid", value="paid"),
    app_commands.Choice(name="🚀 booster", value="booster"),
    app_commands.Choice(name="🔥 extreme", value="extreme")
])
async def add(interaction: discord.Interaction, tier: app_commands.Choice[str], service: str, file: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in STAFF_IDS:
        return await interaction.followup.send("❌ Staff only command.")
    
    content = await file.read()
    valid_lines = [l for l in content.decode("utf-8").splitlines() if l.strip()]
    path = f"{BASE_PATH}/{tier.value}/{service.capitalize()}.txt"
    
    with open(path, "a", encoding="utf-8") as f:
        for line in valid_lines: f.write(line + "\n")
    await interaction.followup.send(f"✅ Successfully added {len(valid_lines)} accounts to {tier.name} -> {service.capitalize()}")

# --- Additional Admin Commands ---
@bot.tree.command(name="addv")
async def addv(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id not in STAFF_IDS: return
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,))
    cursor.execute("UPDATE users SET vouches = vouches + ? WHERE user_id = ?", (amount, member.id))
    db.commit()
    await interaction.response.send_message(f"✅ Added {amount} vouches to {member.mention}")

@bot.tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT user_id, gens FROM users ORDER BY gens DESC LIMIT 10")
    rows = cursor.fetchall()
    lb = "\n".join([f"**{i+1}.** <@{r[0]}> — `{r[1]}` gens" for i, r in enumerate(rows)])
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Top Generators", description=lb or "No data available"))

@bot.tree.command(name="send")
async def send(interaction: discord.Interaction, member: discord.Member, service: str, tier: str):
    if interaction.user.id not in STAFF_IDS: return
    path = f"{BASE_PATH}/{tier.lower()}/{service.capitalize()}.txt"
    if get_stock_count(tier.lower(), service) > 0:
        with open(path, "r") as f: lines = f.readlines()
        acc = lines.pop(0).strip()
        with open(path, "w") as f: f.writelines(lines)
        await member.send(f"🎁 Manual Gift: `{acc}` from {service} ({tier})")
        await interaction.response.send_message(f"✅ Sent to {member.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Out of stock!", ephemeral=True)

@bot.tree.command(name="remove")
async def remove(interaction: discord.Interaction, tier: str, service: str, amount: int):
    if interaction.user.id not in STAFF_IDS: return
    path = f"{BASE_PATH}/{tier.lower()}/{service.capitalize()}.txt"
    if os.path.exists(path):
        with open(path, "r") as f: lines = f.readlines()
        with open(path, "w") as f: f.writelines(lines[amount:])
        await interaction.response.send_message(f"🗑️ Removed {amount} accounts from {tier} -> {service}")

if __name__ == "__main__":
    bot.run(TOKEN)
    
