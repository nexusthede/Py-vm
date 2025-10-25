import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = None

# Emoji mapping
VC_EMOJIS = {
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
    "dash": "<:dashv:1431213611858002010>"
}

# Helper for embed creation
def create_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=discord.Color.blue())

# Button setup for VC control
class VCControlView(View):
    def __init__(self, member_vc):
        super().__init__(timeout=None)
        self.member_vc = member_vc

        for action in ["lock", "unlock", "kick", "ban", "permit", "limit", "reset", "info", "rename", "transfer"]:
            self.add_item(Button(emoji=VC_EMOJIS[action], style=discord.ButtonStyle.gray, custom_id=f"vc_{action}"))

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.voice and interaction.user.voice.channel == self.member_vc

# Setup categories and interface
async def setup_categories_and_interface(guild: discord.Guild):
    # 1️⃣ Unmute Category
    unmute_category = discord.utils.get(guild.categories, name="Unmute")
    if not unmute_category:
        unmute_category = await guild.create_category("Unmute")
        await guild.create_voice_channel("Unmute 1", category=unmute_category)
        await guild.create_voice_channel("Unmute 2", category=unmute_category)

    # 2️⃣ Join-to-Create Category
    join_category = discord.utils.get(guild.categories, name="Join-to-Create")
    if not join_category:
        join_category = await guild.create_category("Join-to-Create")
        public_vc = await guild.create_voice_channel("Create Public VC", category=join_category)
        private_vc = await guild.create_voice_channel("Create Private VC", category=join_category)
        random_vc = await guild.create_voice_channel("Join a Random VC", category=join_category)

        # Send interface message with buttons
        view = View()
        for emoji in ["🔒", "🔓", "🎛️"]:  # Example emojis for join/create
            view.add_item(Button(emoji=emoji, style=discord.ButtonStyle.gray))
        channel = guild.text_channels[0]  # Replace with your interface text channel
        await channel.send(embed=create_embed("Join-to-Create VC", "Press a button to create or join a VC"), view=view)

# Prefix command
@bot.command()
async def vm(ctx):
    await ctx.send(embed=create_embed("VM", "Use `/vm_setup` or buttons in the interface."))

# Slash command
@bot.tree.command(name="vm_setup")
async def slash_vm_setup(interaction: discord.Interaction):
    await interaction.response.send_message("Setting up VC system...", ephemeral=True)
    await setup_categories_and_interface(GUILD)
    await interaction.followup.send(embed=create_embed("Setup Complete", "VC categories and interface created successfully."), ephemeral=True)

# Button interaction
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.data.get("custom_id"):
        return
    cid = interaction.data["custom_id"]
    if cid.startswith("vc_"):
        action = cid[3:]
        vc = interaction.user.voice.channel
        if not vc:
            await interaction.response.send_message("You are not in a VC!", ephemeral=True)
            return
        if action == "lock":
            await vc.set_permissions(interaction.guild.default_role, connect=False)
            await interaction.response.send_message("VC locked 🔒", ephemeral=True)
        elif action == "unlock":
            await vc.set_permissions(interaction.guild.default_role, connect=True)
            await interaction.response.send_message("VC unlocked 🔓", ephemeral=True)
        elif action == "kick":
            # This requires selecting member
            await interaction.response.send_message("Kick action pressed.", ephemeral=True)
        elif action == "ban":
            await interaction.response.send_message("Ban action pressed.", ephemeral=True)
        elif action == "permit":
            await interaction.response.send_message("Permit action pressed.", ephemeral=True)
        elif action == "limit":
            await interaction.response.send_message("Limit action pressed.", ephemeral=True)
        elif action == "reset":
            await interaction.response.send_message("Reset action pressed.", ephemeral=True)
        elif action == "info":
            await interaction.response.send_message(f"VC Info: {vc.name}", ephemeral=True)
        elif action == "rename":
            await interaction.response.send_message("Rename action pressed.", ephemeral=True)
        elif action == "transfer":
            await interaction.response.send_message("Transfer action pressed.", ephemeral=True)

# Ready event
@bot.event
async def on_ready():
    global GUILD
    GUILD = bot.get_guild(GUILD_ID)
    print(f"Logged in as {bot.user}")
    try:
        await bot.tree.sync(guild=GUILD)
        print("Slash commands synced.")
    except Exception as e:
        print(e)

bot.run(os.getenv("TOKEN"))
