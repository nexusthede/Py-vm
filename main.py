# main.py
import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== Emoji Constants ==========
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
    "transfer": "<:transferv:1431213610348183582>"
}

# ========== VC Buttons ==========
class VCButtons(ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

        # Adding each emoji button
        self.add_item(ui.Button(emoji=EMOJIS["lock"], style=discord.ButtonStyle.grey, custom_id="vc_lock"))
        self.add_item(ui.Button(emoji=EMOJIS["unlock"], style=discord.ButtonStyle.grey, custom_id="vc_unlock"))
        self.add_item(ui.Button(emoji=EMOJIS["kick"], style=discord.ButtonStyle.grey, custom_id="vc_kick"))
        self.add_item(ui.Button(emoji=EMOJIS["ban"], style=discord.ButtonStyle.grey, custom_id="vc_ban"))
        self.add_item(ui.Button(emoji=EMOJIS["permit"], style=discord.ButtonStyle.grey, custom_id="vc_permit"))
        self.add_item(ui.Button(emoji=EMOJIS["limit"], style=discord.ButtonStyle.grey, custom_id="vc_limit"))
        self.add_item(ui.Button(emoji=EMOJIS["reset"], style=discord.ButtonStyle.grey, custom_id="vc_reset"))
        self.add_item(ui.Button(emoji=EMOJIS["info"], style=discord.ButtonStyle.grey, custom_id="vc_info"))
        self.add_item(ui.Button(emoji=EMOJIS["edit"], style=discord.ButtonStyle.grey, custom_id="vc_rename"))
        self.add_item(ui.Button(emoji=EMOJIS["transfer"], style=discord.ButtonStyle.grey, custom_id="vc_transfer"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Ensure only VC owner can use buttons
        if interaction.user.id != self.vc.owner_id:
            await interaction.response.send_message("You are not the VC owner!", ephemeral=True)
            return False
        return True

    @ui.button(custom_id="vc_lock")
    async def lock(self, interaction: discord.Interaction, button: ui.Button):
        await self.vc.edit(user_limit=0)
        embed = discord.Embed(description=f"{EMOJIS['lock']} VC locked.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(custom_id="vc_unlock")
    async def unlock(self, interaction: discord.Interaction, button: ui.Button):
        await self.vc.edit(user_limit=None)
        embed = discord.Embed(description=f"{EMOJIS['unlock']} VC unlocked.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Add other buttons similarly: kick, ban, permit, limit, reset, info, rename, transfer
    # Each should send a blue embed confirmation

# ========== VM Setup Command ==========
@bot.tree.command(name="vm_setup", description="Setup all VC categories and interface")
async def vm_setup(interaction: discord.Interaction):
    guild = interaction.guild

    # Check if already exists
    existing_categories = {c.name: c for c in guild.categories}
    
    # 1️⃣ Unmute Category
    if "Unmute" not in existing_categories:
        unmute_cat = await guild.create_category("Unmute")
        await guild.create_voice_channel("Unmute 1", category=unmute_cat)
        await guild.create_voice_channel("Unmute 2", category=unmute_cat)

    # 2️⃣ Join-to-Create Category
    if "Join-to-Create" not in existing_categories:
        create_cat = await guild.create_category("Join-to-Create")
        await guild.create_voice_channel("Create Public VC", category=create_cat)
        await guild.create_voice_channel("Create Private VC", category=create_cat)
        await guild.create_voice_channel("Join a Random VC", category=create_cat)

        # Add interface message in text channel
        interface_channel = await guild.create_text_channel("vc-interface")
        embed = discord.Embed(title="VC Interface", description="Use the buttons below to control your VC", color=discord.Color.blue())
        await interface_channel.send(embed=embed, view=VCButtons(None))  # VC set dynamically when used

    await interaction.response.send_message("VM setup completed.", ephemeral=True)

# ========== Event to Handle Join-to-Create Logic ==========
@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if after.channel:
        # Handle Public VC temp deletion
        if after.channel.name == "Create Public VC":
            new_vc = await guild.create_voice_channel(f"{member.display_name}'s Public VC", category=after.channel.category)
            await member.move_to(new_vc)
        # Handle Private VC temp deletion
        elif after.channel.name == "Create Private VC":
            new_vc = await guild.create_voice_channel(f"{member.display_name}'s Private VC", category=after.channel.category)
            await member.move_to(new_vc)
            await new_vc.set_permissions(member, connect=True, manage_channels=True)

        # Join a Random VC logic
        elif after.channel.name == "Join a Random VC":
            random_vcs = [c for c in after.channel.category.voice_channels if c.name not in ["Create Public VC","Create Private VC","Join a Random VC"]]
            if random_vcs:
                await member.move_to(random.choice(random_vcs))

# Run Bot
bot.run("TOKEN")
