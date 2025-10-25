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

# --- Load or create data.json ---
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
    await bot.tree.sync()
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

    # --- Handle join-to-create channels ---
    join_cat = discord.utils.get(member.guild.categories, name=guild_data["join_to_create_category"])
    if after.channel and after.channel.category == join_cat:
        # Only create VC if user joined a join-to-create channel
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

    # --- Handle unmute VC ---
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

# --- VM Setup / Reset ---
@bot.command()
async def vm(ctx, action=None):
    guild_id = str(ctx.guild.id)
    register_server(ctx.guild)
    guild_data = data["servers"][guild_id]

    if action == "setup":
        categories = await create_vc_categories(ctx.guild)

        # Create 3 join-to-create channels inside JOIN-TO-CREATE
        existing_jtcs = [ch.name for ch in categories["JOIN-TO-CREATE"].channels]
        for i in range(1, 4):
            name = f"Join-{i}"
            if name not in existing_jtcs:
                await ctx.guild.create_voice_channel(name, category=categories["JOIN-TO-CREATE"])

        # Send interface embed
        embed = discord.Embed(
            title="**EDIT YOUR VC BY USING THE BUTTONS BELOW:**",
            description=(
                "<:lockv:1431214489981812778> `vc lock` <:dashv:1431213611858002010> Locks the VC\n"
                "<:unlockv:1431214488316674128> `vc unlock` <:dashv:1431213611858002010> Unlocks the VC\n"
                "<:kickv:1431213595986755725> `vc kick` <:dashv:1431213611858002010> Kicks a user from the VC\n"
                "<:banv:1431213597966598244> `vc ban` <:dashv:1431213611858002010> Bans a user from the VC\n"
                "<:permitv:1431213599774478407> `vc permit` <:dashv:1431213611858002010> Permits a user to the VC\n"
                "<:limitv:1431213601787744367> `vc limit` <:dashv:1431213611858002010> Changes the VC limit\n"
                "<:resetv:1431213603536506890> `vc reset` <:dashv:1431213611858002010> Resets the VC limit and perms\n"
                "<:infov:1431213604895719565> `vc info` <:dashv:1431213611858002010> Shows info about the VC\n"
                "<:editv:1431213607814828113> `vc rename` <:dashv:1431213611858002010> Changes the VC name\n"
                "<:transferv:1431213610348183582> `vc transfer` <:dashv:1431213611858002010> Transfers the VC ownership"
            ),
            color=0x0000FF
        )
        await ctx.send(embed=embed)
        await ctx.send("<:checkv:1431397623193010257> VM setup completed!")

    elif action == "reset":
        # Delete all VCs created by join-to-create
        for vc_id in list(guild_data["vcs"].keys()):
            vc = discord.utils.get(ctx.guild.voice_channels, id=int(vc_id))
            if vc:
                await vc.delete()
            del guild_data["vcs"][vc_id]
        save_data()
        await ctx.send("<:checkv:1431397623193010257> VM reset completed!")

    else:
        await ctx.send("<:failv:1431396982768930929> Invalid vm command!")

# --- Slash VM Command ---
@bot.tree.command(name="vm", description="Setup or reset VM system")
@app_commands.choices(action=[
    app_commands.Choice(name="setup", value="setup"),
    app_commands.Choice(name="reset", value="reset")
])
async def vm_slash(interaction: discord.Interaction, action: app_commands.Choice[str]):
    ctx = await bot.get_context(interaction)
    await vm(ctx, action.value)
    await interaction.response.send_message(f"<:checkv:1431397623193010257> VM {action.value} executed!", ephemeral=True)

# --- VC Commands (Prefix & Slash) ---
@bot.command()
async def vc(ctx, action=None, member: discord.Member=None, limit: int=None):
    guild_id = str(ctx.guild.id)
    register_server(ctx.guild)
    guild_data = data["servers"][guild_id]

    user_vc = ctx.author.voice.channel if ctx.author.voice else None
    if not user_vc or str(user_vc.id) not in guild_data["vcs"]:
        await ctx.send("<:failv:1431396982768930929> You must be in your VC!")
        return

    vc_info = guild_data["vcs"][str(user_vc.id)]

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
    elif action == "limit"
