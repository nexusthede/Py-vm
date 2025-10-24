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

# Load data.json
if not os.path.exists("data.json"):
    with open("data.json", "w") as f:
        json.dump({"servers": {}}, f, indent=4)

with open("data.json", "r") as f:
    data = json.load(f)

def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

# --- Helper functions ---
async def create_vc_categories(guild):
    categories = {}
    for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
        categories[cat_name] = category
    return categories

def register_server(guild):
    if str(guild.id) not in data["servers"]:
        data["servers"][str(guild.id)] = {
            "join_to_create_category": "JOIN-TO-CREATE",
            "public_category": "PUBLIC VCS",
            "private_category": "PRIVATE VCS",
            "unmute_category": "UNMUTE",
            "vcs": {}
        }
        save_data()

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_guild_join(guild):
    register_server(guild)
    await create_vc_categories(guild)

# --- Join-to-create VC ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild_id = str(member.guild.id)
    register_server(member.guild)

    guild_data = data["servers"][guild_id]

    # Join-to-create VC
    join_cat = discord.utils.get(member.guild.categories, name=guild_data["join_to_create_category"])
    if after.channel and after.channel.category == join_cat:
        # Decide type: public or private
        vc_type = "public" if after.channel.name.lower() == "public" else "private"
        target_cat = discord.utils.get(member.guild.categories, name=guild_data[f"{vc_type}_category"])
        new_vc = await member.guild.create_voice_channel(f"{member.name}'s VC", category=target_cat)
        await member.move_to(new_vc)

        # Save VC info
        guild_data["vcs"][str(new_vc.id)] = {
            "owner": member.id,
            "type": vc_type,
            "original_category": target_cat.name,
            "limit": None
        }
        save_data()

    # Handle unmute VC
    unmute_cat = discord.utils.get(member.guild.categories, name=guild_data["unmute_category"])
    if after.channel and after.channel.category == unmute_cat:
        original_vc_id = None
        for vc_id, info in guild_data["vcs"].items():
            if info["owner"] == member.id:
                original_vc_id = int(vc_id)
        if original_vc_id:
            original_vc = discord.utils.get(member.guild.voice_channels, id=original_vc_id)
            if original_vc:
                await member.move_to(original_vc)

# --- Interface ---
@bot.command()
async def interface(ctx):
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
    await ctx.send(embed=embed)

# --- Prefix Commands ---
@bot.command()
async def vc(ctx, action=None, member: discord.Member=None, limit: int=None):
    guild_id = str(ctx.guild.id)
    register_server(ctx.guild)
    guild_data = data["servers"][guild_id]

    # Check user's VC
    user_vc = ctx.author.voice.channel if ctx.author.voice else None
    if not user_vc or str(user_vc.id) not in guild_data["vcs"]:
        await ctx.send("<:failv:1431396982768930929> You must be in your VC!")
        return

    if action == "lock":
        await user_vc.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send("<:checkv:1431397623193010257> VC locked!")
    elif action == "unlock":
        await user_vc.set_permissions(ctx.guild.default_role, connect=True)
        await ctx.send("<:checkv:1431397623193010257> VC unlocked!")
    elif action == "kick" and member:
        await member.move_to(None)
        await ctx.send(f"<:checkv:1431397623193010257> Kicked {member.name}")
    elif action == "ban" and member:
        await user_vc.set_permissions(member, connect=False)
        await ctx.send(f"<:checkv:1431397623193010257> Banned {member.name}")
    elif action == "permit" and member:
        await user_vc.set_permissions(member, connect=True)
        await ctx.send(f"<:checkv:1431397623193010257> Permitted {member.name}")
    elif action == "limit" and limit is not None:
        await user_vc.edit(user_limit=limit)
        guild_data["vcs"][str(user_vc.id)]["limit"] = limit
        save_data()
        await ctx.send(f"<:checkv:1431397623193010257> Limit set to {limit}")
    elif action == "reset":
        await user_vc.edit(user_limit=None)
        await user_vc.set_permissions(ctx.guild.default_role, connect=True)
        guild_data["vcs"][str(user_vc.id)]["limit"] = None
        save_data()
        await ctx.send("<:checkv:1431397623193010257> Reset VC!")
    elif action == "info":
        vc_info = guild_data["vcs"].get(str(user_vc.id))
        await ctx.send(f"Owner: <@{vc_info['owner']}>\nType: {vc_info['type']}\nLimit: {vc_info['limit']}")
    elif action == "rename" and member:
        # member param here is actually name
        await user_vc.edit(name=str(member))
        await ctx.send(f"<:checkv:1431397623193010257> Renamed VC to {member}")
    elif action == "transfer" and member:
        guild_data["vcs"][str(user_vc.id)]["owner"] = member.id
        save_data()
        await ctx.send(f"<:checkv:1431397623193010257> Transferred ownership to {member.name}")
    else:
        await ctx.send("<:failv:1431396982768930929> Invalid command!")

# --- Slash command fallback ---
@bot.tree.command(name="interface", description="Shows the VC interface")
async def slash_interface(interaction: discord.Interaction):
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
    await interaction.response.send_message(embed=embed)

# --- Keep bot alive ---
keep_alive()
bot.run(TOKEN)
