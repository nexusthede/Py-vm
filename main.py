import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

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
    "edit": "<:editv:1431213607814828113>",
    "transfer": "<:transferv:1431213610348183582>",
    "check": "<:checkv:1431397623193010257>",
    "fail": "<:failv:1431396982768930929>"
}

# Store interface message ID and guild data
guild_data = {}

# HELPER: Create category if not exists
async def get_or_create_category(guild, name):
    for cat in guild.categories:
        if cat.name == name:
            return cat
    return await guild.create_category(name)

# HELPER: Create channel if not exists
async def get_or_create_channel(cat, name, type=discord.ChannelType.voice):
    for ch in cat.channels:
        if ch.name == name:
            return ch
    return await cat.create_voice_channel(name)

# EMBED TEMPLATE
def create_embed(title: str, description: str):
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )

# SETUP COMMAND
@bot.command()
async def vm(ctx):
    await ctx.send("Use `.vm setup` or `.vm reset`!")

@bot.command()
async def vm_setup(ctx):
    guild = ctx.guild
    guild_data[guild.id] = {}

    # Categories
    unmute_cat = await get_or_create_category(guild, "UNMUTE")
    join_cat = await get_or_create_category(guild, "JOIN TO CREATE")
    public_cat = await get_or_create_category(guild, "PUBLIC VCS")
    private_cat = await get_or_create_category(guild, "PRIVATE VCS")

    # Unmute channels
    for i in range(1, 3):
        await get_or_create_channel(unmute_cat, f"Unmute {i}")

    # Join-to-create channels
    jtcs = ["Create Public VC", "Create Private VC", "Join a Random VC"]
    for name in jtcs:
        await get_or_create_channel(join_cat, name)

    # Interface message
    embed = create_embed(
        "VC Interface",
        f"{EMOJIS['lock']} Lock  {EMOJIS['unlock']} Unlock  {EMOJIS['kick']} Kick  "
        f"{EMOJIS['ban']} Ban  {EMOJIS['permit']} Permit  {EMOJIS['limit']} Limit  "
        f"{EMOJIS['reset']} Reset  {EMOJIS['info']} Info  {EMOJIS['edit']} Rename  "
        f"{EMOJIS['transfer']} Transfer"
    )

    # Button view
    class VCButtons(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(emoji=EMOJIS["lock"], style=discord.ButtonStyle.gray)
        async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
            vc = interaction.user.voice.channel
            await vc.set_permissions(interaction.guild.default_role, connect=False)
            await interaction.response.send_message(f"{EMOJIS['check']} Locked VC", ephemeral=True)

        @discord.ui.button(emoji=EMOJIS["unlock"], style=discord.ButtonStyle.gray)
        async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
            vc = interaction.user.voice.channel
            await vc.set_permissions(interaction.guild.default_role, connect=True)
            await interaction.response.send_message(f"{EMOJIS['check']} Unlocked VC", ephemeral=True)

        @discord.ui.button(emoji=EMOJIS["kick"], style=discord.ButtonStyle.gray)
        async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
            vc = interaction.user.voice.channel
            for member in vc.members:
                if member != interaction.user:
                    await member.move_to(None)
            await interaction.response.send_message(f"{EMOJIS['check']} Kicked users", ephemeral=True)

    interface_msg = await join_cat.send(embed=embed, view=VCButtons())
    guild_data[guild.id]["interface"] = interface_msg.id

    await ctx.send(embed=create_embed("VM Setup", f"{EMOJIS['check']} VM setup completed!"))

# RESET COMMAND
@bot.command()
async def vm_reset(ctx):
    guild = ctx.guild

    # Delete categories if they exist
    for name in ["UNMUTE", "JOIN TO CREATE", "PUBLIC VCS", "PRIVATE VCS"]:
        for cat in guild.categories:
            if cat.name == name:
                for ch in cat.channels:
                    await ch.delete()
                await cat.delete()

    # Delete interface message
    if guild.id in guild_data:
        guild_data.pop(guild.id)

    await ctx.send(embed=create_embed("VM Reset", f"{EMOJIS['check']} VM reset completed!"))

# SLASH COMMANDS
@tree.command(name="vm", description="VM commands")
async def slash_vm(interaction: discord.Interaction):
    await interaction.response.send_message("Use `/vm setup` or `/vm reset`!", ephemeral=True)

@tree.command(name="vm_setup", description="Setup VM")
async def slash_vm_setup(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction.message)
    await vm_setup(ctx)
    await interaction.response.send_message(f"{EMOJIS['check']} VM setup completed!", ephemeral=True)

@tree.command(name="vm_reset", description="Reset VM")
async def slash_vm_reset(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction.message)
    await vm_reset(ctx)
    await interaction.response.send_message(f"{EMOJIS['check']} VM reset completed!", ephemeral=True)

# READY
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(os.getenv("TOKEN"))
