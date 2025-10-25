import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from keep_alive import keep_alive

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)
tree = bot.tree

if os.path.exists("data.json"):
    with open("data.json", "r") as f:
        guild_data = json.load(f)
else:
    guild_data = {}

def save_data():
    with open("data.json", "w") as f:
        json.dump(guild_data, f, indent=4)

# --- EMBED HELPERS ---
def blue_embed(title="", description=""):
    return discord.Embed(title=title, description=description, color=0x3498db)

def interface_embed():
    desc = (
        "<:lockv:1431214489981812778> `vc lock` <:dashv:1431213611858002010> Locks the VC\n"
        "<:unlockv:1431214488316674128> `vc unlock` <:dashv:1431213611858002010> Unlocks the VC\n"
        "<:kickv:1431213595986755725> `vc kick` <:dashv:1431213611858002010> Kicks a user\n"
        "<:banv:1431213597966598244> `vc ban` <:dashv:1431213611858002010> Bans a user\n"
        "<:permitv:1431213599774478407> `vc permit` <:dashv:1431213611858002010> Permits a user\n"
        "<:limitv:1431213601787744367> `vc limit` <:dashv:1431213611858002010> Sets VC limit\n"
        "<:resetv:1431213603536506890> `vc reset` <:dashv:1431213611858002010> Resets VC perms\n"
        "<:infov:1431213604895719565> `vc info` <:dashv:1431213611858002010> Shows info\n"
        "<:editv:1431213607814828113> `vc rename` <:dashv:1431213611858002010> Rename VC\n"
        "<:transferv:1431213610348183582> `vc transfer` <:dashv:1431213611858002010> Transfer ownership"
    )
    return blue_embed("VC INTERFACE", desc)

# --- BUTTONS ---
class VCButtons(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("<:failv:1431396982768930929> Only VC owner can use this!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Lock VC", style=discord.ButtonStyle.red, custom_id="lock_vc")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("<:checkv:1431397623193010257> VC Locked!", ephemeral=True)

    @discord.ui.button(label="Unlock VC", style=discord.ButtonStyle.green, custom_id="unlock_vc")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("<:checkv:1431397623193010257> VC Unlocked!", ephemeral=True)

    @discord.ui.button(label="Reset VC", style=discord.ButtonStyle.blurple, custom_id="reset_vc")
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.user.voice.channel
        await vc.edit(user_limit=None)
        await interaction.response.send_message("<:checkv:1431397623193010257> VC Reset!", ephemeral=True)

# --- VM SETUP ---
async def create_vm_setup(ctx_or_inter):
    if isinstance(ctx_or_inter, discord.Interaction):
        ctx = await bot.get_context(ctx_or_inter)
    else:
        ctx = ctx_or_inter

    guild_id = str(ctx.guild.id)
    if guild_id not in guild_data:
        guild_data[guild_id] = {"categories": {}, "vcs": {}}

    # Create categories
    join_cat = await ctx.guild.create_category("Join-to-Create")
    unmute_cat = await ctx.guild.create_category("Unmute VC")
    guild_data[guild_id]["categories"]["join"] = join_cat.id
    guild_data[guild_id]["categories"]["unmute"] = unmute_cat.id
    save_data()

    # Create 3 join-to-create channels
    for i in range(1, 4):
        await ctx.guild.create_voice_channel(f"Join VC {i}", category=join_cat)

    embed = interface_embed()
    await ctx.send(embed=embed, view=VCButtons(ctx.author.id))
    await ctx.send("<:checkv:1431397623193010257> VM setup completed!")

@bot.command()
async def vm_setup(ctx):
    await create_vm_setup(ctx)

@tree.command(name="vm_setup", description="Setup VC system")
async def slash_vm_setup(interaction: discord.Interaction):
    await create_vm_setup(interaction)
    await interaction.response.send_message("<:checkv:1431397623193010257> VM setup completed!", ephemeral=True)

# --- VM RESET ---
async def create_vm_reset(ctx_or_inter):
    if isinstance(ctx_or_inter, discord.Interaction):
        ctx = await bot.get_context(ctx_or_inter)
    else:
        ctx = ctx_or_inter

    guild_id = str(ctx.guild.id)
    if guild_id in guild_data:
        guild_data[guild_id] = {"categories": {}, "vcs": {}}
        save_data()
    await ctx.send("<:checkv:1431397623193010257> VM reset completed!")

@bot.command()
async def vm_reset(ctx):
    await create_vm_reset(ctx)

@tree.command(name="vm_reset", description="Reset VC system")
async def slash_vm_reset(interaction: discord.Interaction):
    await create_vm_reset(interaction)
    await interaction.response.send_message("<:checkv:1431397623193010257> VM reset completed!", ephemeral=True)

# --- VC COMMANDS ---
@bot.command()
async def vc(ctx, action: str, member: discord.Member = None, number: int = None):
    if not ctx.author.voice:
        await ctx.send("<:failv:1431396982768930929> You are not in a VC!")
        return
    vc = ctx.author.voice.channel
    guild_id = str(ctx.guild.id)

    if action.lower() == "info":
        desc = f"**Name:** {vc.name}\n**Members:** {len(vc.members)}\n**Category:** {vc.category.name}"
        await ctx.send(embed=blue_embed("VC INFO", desc))
    elif action.lower() == "reset":
        await vc.edit(user_limit=None)
        await ctx.send("<:checkv:1431397623193010257> VC reset!")
    elif action.lower() == "limit" and number:
        await vc.edit(user_limit=number)
        await ctx.send(f"<:checkv:1431397623193010257> VC limit set to {number}!")

# --- START BOT ---
keep_alive()
bot.run(os.getenv("TOKEN"))
