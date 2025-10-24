import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from keep_alive import keep_alive

# Load environment variable
TOKEN = os.environ.get("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)

# Load or create data.json
if not os.path.exists("data.json"):
    with open("data.json", "w") as f:
        json.dump({"servers": {}}, f, indent=4)

with open("data.json", "r") as f:
    data = json.load(f)

def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

# --- Helper functions ---
async def create_categories_and_channels(guild):
    categories = {}
    for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
        categories[cat_name] = category

    # Join-to-create VC channels
    join_cat = categories["JOIN-TO-CREATE"]
    for vc_name in ["Public VC", "Private VC", "Random VC"]:
        if not discord.utils.get(join_cat.voice_channels, name=vc_name):
            await guild.create_voice_channel(vc_name, category=join_cat)

    # Interface channel
    interface_name = "interface"
    if not discord.utils.get(guild.text_channels, name=interface_name):
        interface = await guild.create_text_channel(interface_name)
        await send_interface_embed(interface)

    return categories

async def send_interface_embed(channel):
    embed = discord.Embed(
        title="**EDIT YOUR VC BY USING THE BUTTONS BELOW:**",
        description=(
            "`<:lockv:1431214489981812778>` - Locks the VC\n"
            "`<:unlockv:1431214488316674128>` - Unlocks the VC\n"
            "`<:kickv:1431213595986755725>` - Kicks a user\n"
            "`<:banv:1431213597966598244>` - Bans a user\n"
            "`<:permitv:1431213599774478407>` - Permits a user\n"
            "`<:limitv:1431213601787744367>` - Changes VC limit\n"
            "`<:resetv:1431213603536506890>` - Resets VC\n"
            "`<:infov:1431213604895719565>` - Shows VC info\n"
            "`<:renamev:1431213607814828113>` - Renames VC\n"
            "`<:transferv:1431213610348183582>` - Transfers VC ownership"
        ),
        color=0x32CD32
    )
    await channel.send(embed=embed)

def register_server(guild):
    if str(guild.id) not in data["servers"]:
        data["servers"][str(guild.id)] = {"vcs": {}}
        save_data()

def unregister_server(guild):
    if str(guild.id) in data["servers"]:
        del data["servers"][str(guild.id)]
        save_data()

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Error syncing slash commands: {e}")

# Join-to-create VC
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild = member.guild
    register_server(guild)
    guild_data = data["servers"][str(guild.id)]

    # Join-to-create
    join_cat = discord.utils.get(guild.categories, name="JOIN-TO-CREATE")
    if after.channel and after.channel.category == join_cat:
        # Decide type
        vc_type = "public" if after.channel.name.lower() == "public vc" else "private"
        target_cat = discord.utils.get(guild.categories, name=f"{vc_type.upper()} VCS")
        new_vc = await guild.create_voice_channel(f"{member.name}'s VC", category=target_cat)
        await member.move_to(new_vc)

        guild_data["vcs"][str(new_vc.id)] = {"owner": member.id, "type": vc_type, "limit": None}
        save_data()

    # Unmute category
    unmute_cat = discord.utils.get(guild.categories, name="UNMUTE")
    if after.channel and after.channel.category == unmute_cat:
        original_vc_id = None
        for vc_id, info in guild_data["vcs"].items():
            if info["owner"] == member.id:
                original_vc_id = int(vc_id)
        if original_vc_id:
            original_vc = discord.utils.get(guild.voice_channels, id=original_vc_id)
            if original_vc:
                await member.move_to(original_vc)

# --- Prefix VM commands ---
@bot.command()
async def vm(ctx, action=None):
    guild = ctx.guild
    if action == "setup":
        await create_categories_and_channels(guild)
        register_server(guild)
        await ctx.send("<:checkv:1431397623193010257> VM setup complete!")
    elif action == "reset":
        # Delete categories and interface channel
        for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
            category = discord.utils.get(guild.categories, name=cat_name)
            if category:
                for vc in category.voice_channels:
                    await vc.delete()
                await category.delete()
        interface_channel = discord.utils.get(guild.text_channels, name="interface")
        if interface_channel:
            await interface_channel.delete()
        unregister_server(guild)
        await ctx.send("<:checkv:1431397623193010257> VM reset complete!")
    else:
        await ctx.send("<:failv:1431396982768930929> Invalid VM command!")

# --- Slash VM commands ---
@bot.tree.command(name="vm", description="Manage Voice Master setup")
@app_commands.describe(action="setup or reset")
async def slash_vm(interaction: discord.Interaction, action: str):
    guild = interaction.guild
    if action == "setup":
        await create_categories_and_channels(guild)
        register_server(guild)
        await interaction.response.send_message("<:checkv:1431397623193010257> VM setup complete!")
    elif action == "reset":
        for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
            category = discord.utils.get(guild.categories, name=cat_name)
            if category:
                for vc in category.voice_channels:
                    await vc.delete()
                await category.delete()
        interface_channel = discord.utils.get(guild.text_channels, name="interface")
        if interface_channel:
            await interface_channel.delete()
        unregister_server(guild)
        await interaction.response.send_message("<:checkv:1431397623193010257> VM reset complete!")
    else:
        await interaction.response.send_message("<:failv:1431396982768930929> Invalid VM command!")

# --- Keep bot alive ---
keep_alive()
bot.run(TOKEN)
