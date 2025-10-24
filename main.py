import os
import json
from discord.ext import commands, tasks
from discord import app_commands, Intents, ui, ButtonStyle
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
PORT = int(os.getenv('PORT', 8000))

intents = Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)

# Data storage for multi-server
DATA_FILE = 'data.json'
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ---------- Keep-alive Flask server ----------
app = Flask('')

@app.route('/')
def home():
    return "Voice Master Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=PORT)

Thread(target=run).start()

# ---------- Interface Embed ----------
interface_embed = {
    "title": "EDIT YOUR VC BY USING THE BUTTONS BELOW:",
    "description": (
        "<:lockv:1431214489981812778> .vc lock - Locks the VC\n"
        "<:unlockv:1431214488316674128> .vc unlock - Unlocks the VC\n"
        "<:kickv:1431213595986755725> .vc kick - Kicks a user from the VC\n"
        "<:banv:1431213597966598244> .vc ban - Bans a user from the VC\n"
        "<:permitv:1431213599774478407> .vc permit - Permits a user to the VC\n"
        "<:limitv:1431213601787744367> .vc limit - Changes the VC limit\n"
        "<:resetv:1431213603536506890> .vc reset - Resets the VC limit and perms\n"
        "<:infov:1431213604895719565> .vc info - Shows info about the VC\n"
        "<:renamev:1431213607814828113> .vc rename - Changes the VC name\n"
        "<:transferv:1431213610348183582> .vc transfer - Transfers the VC ownership"
    ),
    "color": 0x32CD32  # Lime
}

# ---------- Buttons ----------
class InterfaceButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="Lock", emoji="<:lockv:1431214489981812778>", style=ButtonStyle.secondary, custom_id="lock"))
        self.add_item(ui.Button(label="Unlock", emoji="<:unlockv:1431214488316674128>", style=ButtonStyle.secondary, custom_id="unlock"))
        self.add_item(ui.Button(label="Kick", emoji="<:kickv:1431213595986755725>", style=ButtonStyle.secondary, custom_id="kick"))
        self.add_item(ui.Button(label="Ban", emoji="<:banv:1431213597966598244>", style=ButtonStyle.secondary, custom_id="ban"))
        self.add_item(ui.Button(label="Permit", emoji="<:permitv:1431213599774478407>", style=ButtonStyle.secondary, custom_id="permit"))
        self.add_item(ui.Button(label="Limit", emoji="<:limitv:1431213601787744367>", style=ButtonStyle.secondary, custom_id="limit"))
        self.add_item(ui.Button(label="Reset", emoji="<:resetv:1431213603536506890>", style=ButtonStyle.secondary, custom_id="reset"))
        self.add_item(ui.Button(label="Info", emoji="<:infov:1431213604895719565>", style=ButtonStyle.secondary, custom_id="info"))
        self.add_item(ui.Button(label="Rename", emoji="<:renamev:1431213607814828113>", style=ButtonStyle.secondary, custom_id="rename"))
        self.add_item(ui.Button(label="Transfer", emoji="<:transferv:1431213610348183582>", style=ButtonStyle.secondary, custom_id="transfer"))

# ---------- Join-to-create VC ----------
@bot.event
async def on_voice_state_update(member, before, after):
    data = load_data()
    guild_id = str(member.guild.id)
    if guild_id not in data:
        data[guild_id] = {}
    # Create VC channels logic
    join_category = None
    public_category = None
    private_category = None
    unmute_category = None
    for cat in member.guild.categories:
        if cat.name.lower() == "join-to-create":
            join_category = cat
        elif cat.name.lower() == "public vcs":
            public_category = cat
        elif cat.name.lower() == "private vcs":
            private_category = cat
        elif cat.name.lower() == "unmute":
            unmute_category = cat

    # When user joins a join-to-create VC
    if after.channel and join_category and after.channel.category_id == join_category.id:
        # Determine VC type
        name = after.channel.name.lower()
        if "public" in name:
            cat = public_category
        elif "private" in name:
            cat = private_category
        elif "random" in name:
            cat = public_category
        else:
            cat = public_category
        # Create a VC
        vc = await member.guild.create_voice_channel(
            f"{member.name}'s VC", category=cat
        )
        await member.move_to(vc)

# ---------- Prefix Commands ----------
@bot.command()
async def vc(ctx, action=None, target=None):
    if action is None:
        await ctx.send("<:failv:1431396982768930929> Please specify an action.")
        return
    action = action.lower()
    if action == "lock":
        await ctx.channel.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send("<:checkv:1431397623193010257> VC locked!")
    elif action == "unlock":
        await ctx.channel.set_permissions(ctx.guild.default_role, connect=True)
        await ctx.send("<:checkv:1431397623193010257> VC unlocked!")
    else:
        await ctx.send("<:failv:1431396982768930929> Unknown action.")

# ---------- Slash Commands ----------
@bot.tree.command(name="vc", description="Manage your VC")
@app_commands.describe(action="Action to perform", target="Target user if applicable")
async def vc_slash(interaction, action: str, target: str = None):
    ctx = interaction
    await vc(ctx, action, target)

# ---------- Interface Command ----------
@bot.command()
async def interface(ctx):
    view = InterfaceButtons()
    await ctx.send(embed=discord.Embed.from_dict(interface_embed), view=view)

# ---------- Start Bot ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
