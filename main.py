import os
import discord
from discord.ext import commands
from discord.utils import get
from flask import Flask
import threading
import asyncio

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.messages = True
intents.message_content = True  # needed for prefix commands

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Custom Emojis
SUCCESS = "<:check_markv:1431619384987615383>"
FAIL = "<:x_markv:1431619387168657479>"

# Category & VC Names
JOIN_CREATE_CATEGORY = "Join to Create"
PUBLIC_CATEGORY = "Public VCs"
PRIVATE_CATEGORY = "Private VCs"
UNMUTE_CATEGORY = "Unmute VCs"

CREATE_PUBLIC_VC = "Create Public VC"
CREATE_PRIVATE_VC = "Create Private VC"

UNMUTE_VCS = ["Unmute VC 1", "Unmute VC 2"]

# Keep track of server setup
server_setup = {}

# ---------- BOT EVENTS ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ---------- BOT COMMANDS ----------
@bot.command(name="vmsetup")
@commands.has_permissions(administrator=True)
async def vmsetup(ctx):
    guild = ctx.guild
    try:
        if guild.id in server_setup:
            await ctx.send(f"{FAIL} VM system already set up for this server.")
            return

        # Create Categories
        join_category = await guild.create_category(JOIN_CREATE_CATEGORY)
        public_category = await guild.create_category(PUBLIC_CATEGORY)
        private_category = await guild.create_category(PRIVATE_CATEGORY)
        unmute_category = await guild.create_category(UNMUTE_CATEGORY)

        # Create Join-to-Create VCs
        await guild.create_voice_channel(CREATE_PUBLIC_VC, category=join_category)
        await guild.create_voice_channel(CREATE_PRIVATE_VC, category=join_category)

        # Create Unmute VCs
        for vc_name in UNMUTE_VCS:
            await guild.create_voice_channel(vc_name, category=unmute_category)

        # Save setup
        server_setup[guild.id] = {
            "join_category": join_category.id,
            "public_category": public_category.id,
            "private_category": private_category.id,
            "unmute_category": unmute_category.id
        }

        await ctx.send(f"{SUCCESS} VM system successfully set up!")

    except Exception as e:
        await ctx.send(f"{FAIL} Failed to set up VM system.\nError: {e}")

@bot.command(name="vmreset")
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    try:
        if guild.id not in server_setup:
            await ctx.send(f"{FAIL} VM system is not set up in this server.")
            return

        setup = server_setup[guild.id]
        for cat_id in setup.values():
            category = get(guild.categories, id=cat_id)
            if category:
                for ch in category.channels:
                    await ch.delete()
                await category.delete()

        server_setup.pop(guild.id)
        await ctx.send(f"{SUCCESS} VM system has been reset.")

    except Exception as e:
        await ctx.send(f"{FAIL} Failed to reset VM system.\nError: {e}")

@bot.command(name="vmcommands")
async def vmcommands(ctx):
    commands_list = (
        ".vmsetup - Setup VM system (Admin only)\n"
        ".vmreset - Reset VM system (Admin only)\n"
        ".vc lock - Lock your VC\n"
        ".vc unlock - Unlock your VC\n"
        ".vc kick - Kick a member from your VC\n"
        ".vc ban - Ban a member from your VC\n"
        ".vc permit - Permit a member to join your VC\n"
        ".vc limit - Set a user limit for your VC\n"
        ".vc rename - Rename your VC\n"
        ".vc transfer - Transfer VC ownership\n"
        ".vc unmute - Unmute your VC"
    )
    await ctx.send(f"**VM & VC Commands:**\n{commands_list}")

# ---------- JOIN TO CREATE HANDLER ----------
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild = member.guild
    if guild.id not in server_setup:
        return

    setup = server_setup[guild.id]
    join_category = get(guild.categories, id=setup["join_category"])

    if after.channel and after.channel.category == join_category:
        # Determine type
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"@{member.name}'s channel"
            perms = None
        else:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"@{member.name}'s channel"
            perms = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True)
            }

        # Create temp VC
        if perms:
            temp_vc = await guild.create_voice_channel(vc_name, category=category, overwrites=perms)
        else:
            temp_vc = await guild.create_voice_channel(vc_name, category=category)

        await member.move_to(temp_vc)

        # Delete VC when empty
        async def delete_when_empty(vc):
            while True:
                await asyncio.sleep(10)
                if len(vc.members) == 0:
                    await vc.delete()
                    break

        bot.loop.create_task(delete_when_empty(temp_vc))

# ---------- VC MASTER COMMANDS ----------
async def get_user_vc(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        return ctx.author.voice.channel
    await ctx.send(f"{FAIL} You are not in a VC!")
    return None

@bot.command(name="vc lock")
async def vc_lock(ctx):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    await vc.set_permissions(ctx.guild.default_role, connect=False)
    await ctx.send(f"{SUCCESS} VC locked!")

@bot.command(name="vc unlock")
async def vc_unlock(ctx):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    await vc.set_permissions(ctx.guild.default_role, connect=True)
    await ctx.send(f"{SUCCESS} VC unlocked!")

@bot.command(name="vc kick")
async def vc_kick(ctx, member: discord.Member):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    try:
        await member.move_to(None)
        await ctx.send(f"{SUCCESS} Kicked {member.name} from the VC!")
    except:
        await ctx.send(f"{FAIL} Could not kick {member.name}.")

@bot.command(name="vc ban")
async def vc_ban(ctx, member: discord.Member):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    try:
        await vc.set_permissions(member, connect=False)
        await member.move_to(None)
        await ctx.send(f"{SUCCESS} Banned {member.name} from the VC!")
    except:
        await ctx.send(f"{FAIL} Could not ban {member.name}.")

@bot.command(name="vc permit")
async def vc_permit(ctx, member: discord.Member):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    try:
        await vc.set_permissions(member, connect=True)
        await ctx.send(f"{SUCCESS} Permitted {member.name} to join the VC!")
    except:
        await ctx.send(f"{FAIL} Could not permit {member.name}.")

@bot.command(name="vc limit")
async def vc_limit(ctx, limit: int):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    await vc.edit(user_limit=limit)
    await ctx.send(f"{SUCCESS} VC user limit set to {limit}!")

@bot.command(name="vc rename")
async def vc_rename(ctx, *, new_name):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    new_vc_name = f"@{ctx.author.name}'s {new_name}"
    await vc.edit(name=new_vc_name)
    await ctx.send(f"{SUCCESS} VC renamed to {new_vc_name}!")

@bot.command(name="vc transfer")
async def vc_transfer(ctx, member: discord.Member):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    try:
        await vc.set_permissions(ctx.author, connect=True, manage_channels=False)
        await vc.set_permissions(member, connect=True, manage_channels=True)
        await ctx.send(f"{SUCCESS} VC ownership transferred to {member.name}!")
    except:
        await ctx.send(f"{FAIL} Could not transfer VC ownership.")

@bot.command(name="vc unmute")
async def vc_unmute(ctx):
    vc = await get_user_vc(ctx)
    if not vc:
        return
    for mem in vc.members:
        await mem.edit(mute=False)
    await ctx.send(f"{SUCCESS} All members unmuted!")

# ---------- FLASK KEEPALIVE ----------
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()
bot.run(TOKEN)
