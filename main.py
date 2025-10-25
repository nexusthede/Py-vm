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
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Emojis
SUCCESS = "✅"
FAIL = "❌"

# Category & VC Names
JOIN_CREATE_CATEGORY = "Join to Create"
PUBLIC_CATEGORY = "Public VCs"
PRIVATE_CATEGORY = "Private VCs"
UNMUTE_CATEGORY = "Unmute VCs"

CREATE_PUBLIC_VC = "Create Public VC"
CREATE_PRIVATE_VC = "Create Private VC"

UNMUTE_VCS = ["Unmute VC 1", "Unmute VC 2"]

# Track server setup
server_setup = {}

# ---------- BOT EVENTS ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ---------- VM COMMANDS ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def vmsetup(ctx):
    guild = ctx.guild
    try:
        if guild.id in server_setup:
            await ctx.send(f"{FAIL} VM system already set up for this server.")
            return

        # Create categories
        join_category = await guild.create_category(JOIN_CREATE_CATEGORY)
        public_category = await guild.create_category(PUBLIC_CATEGORY)
        private_category = await guild.create_category(PRIVATE_CATEGORY)
        unmute_category = await guild.create_category(UNMUTE_CATEGORY)

        # Create join-to-create VCs
        await guild.create_voice_channel(CREATE_PUBLIC_VC, category=join_category)
        await guild.create_voice_channel(CREATE_PRIVATE_VC, category=join_category)

        # Create unmute VCs
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

@bot.command()
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

@bot.command()
async def vmcommands(ctx):
    embed = discord.Embed(title="VM Master Commands", color=discord.Color.blue())
    embed.add_field(name=".vmsetup", value="Setup VM system (Admin only)", inline=False)
    embed.add_field(name=".vmreset", value="Reset VM system (Admin only)", inline=False)
    embed.add_field(name="VC Master", value="Join Public/Private VC to create your own temporary VC", inline=False)
    await ctx.send(embed=embed)

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
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"{member.display_name}'s channel"
            perms = None
        else:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"{member.display_name}'s channel"
            perms = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True)
            }

        if perms:
            temp_vc = await guild.create_voice_channel(vc_name, category=category, overwrites=perms)
        else:
            temp_vc = await guild.create_voice_channel(vc_name, category=category)

        await member.move_to(temp_vc)

        async def delete_when_empty(vc):
            while True:
                await asyncio.sleep(10)
                if len(vc.members) == 0:
                    await vc.delete()
                    break

        bot.loop.create_task(delete_when_empty(temp_vc))

# ---------- VC MASTER COMMANDS ----------
async def get_member_vc(member):
    if member.voice and member.voice.channel:
        return member.voice.channel
    return None

@bot.command()
async def vc_lock(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.set_permissions(ctx.guild.default_role, connect=False)
    await ctx.send(f"{SUCCESS} {vc.name} locked.")

@bot.command()
async def vc_unlock(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.set_permissions(ctx.guild.default_role, connect=True)
    await ctx.send(f"{SUCCESS} {vc.name} unlocked.")

@bot.command()
async def vc_kick(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    if member in vc.members:
        await member.move_to(None)
        await ctx.send(f"{SUCCESS} {member.display_name} kicked from {vc.name}.")
    else:
        await ctx.send(f"{FAIL} {member.display_name} is not in your VC.")

@bot.command()
async def vc_ban(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.set_permissions(member, connect=False)
    if member in vc.members:
        await member.move_to(None)
    await ctx.send(f"{SUCCESS} {member.display_name} banned from {vc.name}.")

@bot.command()
async def vc_permit(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.set_permissions(member, connect=True)
    await ctx.send(f"{SUCCESS} {member.display_name} can now join {vc.name}.")

@bot.command()
async def vc_limit(ctx, limit: int):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.edit(user_limit=limit)
    await ctx.send(f"{SUCCESS} {vc.name} limit set to {limit}.")

@bot.command()
async def vc_rename(ctx, *, name: str):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.edit(name=name)
    await ctx.send(f"{SUCCESS} VC renamed to {name}.")

@bot.command()
async def vc_transfer(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    await vc.set_permissions(member, connect=True, manage_channels=True)
    await vc.set_permissions(ctx.author, manage_channels=False)
    await ctx.send(f"{SUCCESS} Ownership transferred to {member.display_name}.")

@bot.command()
async def vc_unmute(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(f"{FAIL} You are not in a voice channel.")
    for m in vc.members:
        await m.edit(mute=False)
    await ctx.send(f"{SUCCESS} Everyone unmuted in {vc.name}.")

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
