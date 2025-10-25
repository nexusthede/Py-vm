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

# Custom Emojis
SUCCESS = "<:check_markv:1431619384987615383>"
FAIL = "<:x_markv:1431619387168657479>"

# Categories & VC Names
JOIN_CREATE_CATEGORY = "Join to Create"
PUBLIC_CATEGORY = "Public VCs"
PRIVATE_CATEGORY = "Private VCs"
UNMUTE_CATEGORY = "Unmute VCs"

CREATE_PUBLIC_VC = "Create Public VC"
CREATE_PRIVATE_VC = "Create Private VC"

UNMUTE_VCS = ["Unmute VC 1", "Unmute VC 2"]

# Track server setup
server_setup = {}
temp_vcs = {}  # Track temporary VCs per user

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
            embed = discord.Embed(description=f"{FAIL} VM system already set up for this server.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        # Create categories
        join_category = await guild.create_category(JOIN_CREATE_CATEGORY)
        public_category = await guild.create_category(PUBLIC_CATEGORY)
        private_category = await guild.create_category(PRIVATE_CATEGORY)
        unmute_category = await guild.create_category(UNMUTE_CATEGORY)

        # Create join-to-create VCs
        await guild.create_voice_channel(CREATE_PUBLIC_VC, category=join_category)
        await guild.create_voice_channel(CREATE_PRIVATE_VC, category=join_category)

        # Create unmute VCs (avoid duplicates)
        for vc_name in UNMUTE_VCS:
            existing = discord.utils.get(unmute_category.channels, name=vc_name)
            if not existing:
                await guild.create_voice_channel(vc_name, category=unmute_category)

        # Save setup
        server_setup[guild.id] = {
            "join_category": join_category.id,
            "public_category": public_category.id,
            "private_category": private_category.id,
            "unmute_category": unmute_category.id
        }

        embed = discord.Embed(description=f"{SUCCESS} VM system successfully set up!", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(description=f"{FAIL} Failed to set up VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    try:
        if guild.id not in server_setup:
            embed = discord.Embed(description=f"{FAIL} VM system is not set up in this server.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        setup = server_setup[guild.id]
        for cat_id in setup.values():
            category = get(guild.categories, id=cat_id)
            if category:
                for ch in category.channels:
                    try:
                        await ch.delete()
                    except:
                        pass
                try:
                    await category.delete()
                except:
                    pass

        server_setup.pop(guild.id)
        embed = discord.Embed(description=f"{SUCCESS} VM system has been reset.", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(description=f"{FAIL} Failed to reset VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command()
async def vmcommands(ctx):
    embed = discord.Embed(title="VM Master Commands", color=discord.Color.blue())
    embed.add_field(name=".vmsetup", value="Setup VM system (Admin only)", inline=False)
    embed.add_field(name=".vmreset", value="Reset VM system (Admin only)", inline=False)
    embed.add_field(name=".vc", value="Use VC subcommands: lock/unlock/kick/ban/permit/limit/rename/transfer/unmute", inline=False)
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
        # Prevent multiple temp VCs per user
        if member.id in temp_vcs:
            return

        # Determine VC type
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"{member.display_name}'s channel"
            perms = None
        elif after.channel.name == CREATE_PRIVATE_VC:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"{member.display_name}'s channel"
            perms = {guild.default_role: discord.PermissionOverwrite(connect=False),
                     member: discord.PermissionOverwrite(connect=True)}
        else:
            return  # Not a join-to-create VC

        # Create temp VC
        temp_vc = await guild.create_voice_channel(vc_name, category=category, overwrites=perms)
        temp_vcs[member.id] = temp_vc.id
        await member.move_to(temp_vc)

        # Auto-delete when empty
        async def delete_when_empty(vc):
            while True:
                await asyncio.sleep(10)
                try:
                    if len(vc.members) == 0:
                        await vc.delete()
                        temp_vcs.pop(member.id, None)
                        break
                except discord.errors.NotFound:
                    temp_vcs.pop(member.id, None)
                    break

        bot.loop.create_task(delete_when_empty(temp_vc))

# ---------- VC MASTER COMMANDS ----------
async def get_member_vc(member):
    if member.voice and member.voice.channel:
        return member.voice.channel
    return None

@bot.group()
async def vc(ctx):
    if ctx.invoked_subcommand is None:
        embed = discord.Embed(description=f"{FAIL} Invalid VC command. Use `.vc lock/unlock/kick/ban/permit/limit/rename/transfer/unmute`", color=discord.Color.red())
        await ctx.send(embed=embed)

@vc.command()
async def lock(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(embed=discord.Embed(description=f"{FAIL} You are not in a voice channel.", color=discord.Color.red()))
    await vc.set_permissions(ctx.guild.default_role, connect=False)
    await ctx.send(embed=discord.Embed(description=f"{SUCCESS} {vc.name} locked.", color=discord.Color.green()))

@vc.command()
async def unlock(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(embed=discord.Embed(description=f"{FAIL} You are not in a voice channel.", color=discord.Color.red()))
    await vc.set_permissions(ctx.guild.default_role, connect=True)
    await ctx.send(embed=discord.Embed(description=f"{SUCCESS} {vc.name} unlocked.", color=discord.Color.green()))

@vc.command()
async def kick(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(embed=discord.Embed(description=f"{FAIL} You are not in a voice channel.", color=discord.Color.red()))
    if member in vc.members:
        await member.move_to(None)
        await ctx.send(embed=discord.Embed(description=f"{SUCCESS} {member.display_name} kicked from {vc.name}.", color=discord.Color.green()))
    else:
        await ctx.send(embed=discord.Embed(description=f"{FAIL} {member.display_name} is not in your VC.", color=discord.Color.red()))

@vc.command()
async def ban(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(embed=discord.Embed(description=f"{FAIL} You are not in a voice channel.", color=discord.Color.red()))
    await vc.set_permissions(member, connect=False)
    if member in vc.members:
        await member.move_to(None)
    await ctx.send(embed=discord.Embed(description=f"{SUCCESS} {member.display_name} banned from {vc.name}.", color=discord.Color.green()))

@vc.command()
async def permit(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        return await ctx.send(embed=discord.Embed(description=f"{FAIL} You are not in a voice channel.", color=discord.Color.red()))
    await vc.set_permissions(member, connect=True)
    await ctx.send(embed=discord.Embed
