import discord
from discord.ext import commands, tasks
from discord import app_commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

GUILD_ID = int(os.getenv("GUILD_ID"))  # replace with your guild ID or env variable

# Emojis
EMOJIS = {
    "lock": "<:lockv:1431214489981812778>",
    "unlock": "<:unlockv:1431214488316674128>",
    "kick": "<:kickv:1431213595986755725>",
    "ban": "<:banv:1431213597966598244>",
    "permit": "<:permitv:1431213599774478407>",
    "limit": "<:limitv:1431213601787744367>",
    "reset": "<:resetv:1431213603536506890>",
    "info": "<:infov:1431213604895719565>",
    "rename": "<:editv:1431213607814828113>",
    "transfer": "<:transferv:1431213610348183582>",
    "check": "<:checkv:1431397623193010257>",
    "fail": "<:failv:1431396982768930929>"
}

# Store guild VC info
guild_data = {}

# -----------------------
# Embed helper
# -----------------------
def create_embed(title, description, success=True):
    color = discord.Color.blue()
    embed = discord.Embed(title=title, description=description, color=color)
    return embed

# -----------------------
# VM Setup / Reset
# -----------------------
async def setup_vm(ctx):
    guild = ctx.guild
    guild_data[guild.id] = {"vcs": {}, "interface": None}

    # Create categories if not exist
    categories = {}
    for name in ["Join-to-Create", "Public VCs", "Private VCs", "Unmute Public", "Unmute Private"]:
        cat = discord.utils.get(guild.categories, name=name)
        if not cat:
            cat = await guild.create_category(name)
        categories[name] = cat

    # Create join-to-create channels
    for i in range(1, 4):
        chan_name = f"Join VC {i}"
        if not discord.utils.get(categories["Join-to-Create"].channels, name=chan_name):
            await guild.create_voice_channel(chan_name, category=categories["Join-to-Create"])

    # Create interface message
    interface = await categories["Join-to-Create"].text_channels[0].send(
        embed=create_embed("VC Interface", "Use the buttons below to manage your VC!"),
        view=InterfaceView()
    )
    guild_data[guild.id]["interface"] = interface.id

    await ctx.send(embed=create_embed("VM Setup", f"{EMOJIS['check']} VM system setup successfully!"))

async def reset_vm(ctx):
    guild = ctx.guild
    for cat in guild.categories:
        if cat.name in ["Join-to-Create", "Public VCs", "Private VCs", "Unmute Public", "Unmute Private"]:
            for ch in cat.channels:
                await ch.delete()
            await cat.delete()
    guild_data[guild.id] = {}
    await ctx.send(embed=create_embed("VM Reset", f"{EMOJIS['check']} VM system reset successfully!"))

# -----------------------
# Interface buttons
# -----------------------
class InterfaceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lock VC", style=discord.ButtonStyle.red, emoji=EMOJIS["lock"])
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Lock VC", f"{EMOJIS['check']} VC locked."), ephemeral=True)

    @discord.ui.button(label="Unlock VC", style=discord.ButtonStyle.green, emoji=EMOJIS["unlock"])
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Unlock VC", f"{EMOJIS['check']} VC unlocked."), ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.gray, emoji=EMOJIS["kick"])
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Kick VC", f"{EMOJIS['check']} User kicked."), ephemeral=True)

# -----------------------
# Prefix commands
# -----------------------
@bot.command()
async def vm(ctx, action=None):
    if action == "setup":
        await setup_vm(ctx)
    elif action == "reset":
        await reset_vm(ctx)
    else:
        await ctx.send(embed=create_embed("Error", f"{EMOJIS['fail']} Invalid VM command"))

# -----------------------
# Slash commands
# -----------------------
@tree.command(name="vm", description="VM setup/reset", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(action="setup or reset")
async def slash_vm(interaction: discord.Interaction, action: str):
    if action.lower() == "setup":
        await setup_vm(interaction)
    elif action.lower() == "reset":
        await reset_vm(interaction)
    else:
        await interaction.response.send_message(embed=create_embed("Error", f"{EMOJIS['fail']} Invalid VM command"), ephemeral=True)

# -----------------------
# Bot ready
# -----------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync(guild=discord.Object(id=GUILD_ID))

bot.run(os.getenv("TOKEN"))
