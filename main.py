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

# Keep track of server setup and temporary VCs
server_setup = {}
temp_vcs = {}

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
            embed = discord.Embed(title="VM System", description=f"{FAIL} VM system already set up for this server.", color=discord.Color.red())
            await ctx.send(embed=embed)
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

        embed = discord.Embed(title="VM System", description=f"{SUCCESS} VM system successfully set up!", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="VM System Error", description=f"{FAIL} Failed to set up VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command(name="vmreset")
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    try:
        if guild.id not in server_setup:
            embed = discord.Embed(title="VM System", description=f"{FAIL} VM system is not set up in this server.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        setup = server_setup[guild.id]
        for cat_id in setup.values():
            category = get(guild.categories, id=cat_id)
            if category:
                for ch in category.channels:
                    await ch.delete()
                await category.delete()

        server_setup.pop(guild.id)
        temp_vcs.pop(guild.id, None)

        embed = discord.Embed(title="VM System", description=f"{SUCCESS} VM system has been reset.", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="VM System Error", description=f"{FAIL} Failed to reset VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command(name="vmcommands")
async def vmcommands(ctx):
    embed = discord.Embed(title="VM Master Commands", color=discord.Color.blue())
    embed.add_field(name=".vmsetup", value="Setup VM system (Admin only)", inline=False)
    embed.add_field(name=".vmreset", value="Reset VM system (Admin only)", inline=False)
    embed.add_field(name="VC Master", value="Join Public/Private VC to create your own temporary VC", inline=False)
    embed.add_field(name=".vc lock", value="Lock your VC", inline=False)
    embed.add_field(name=".vc unlock", value="Unlock your VC", inline=False)
    embed.add_field(name=".vc kick <member>", value="Kick member from VC", inline=False)
    embed.add_field(name=".vc ban <member>", value="Ban member from VC", inline=False)
    embed.add_field(name=".vc permit <member>", value="Allow member to join VC", inline=False)
    embed.add_field(name=".vc limit <number>", value="Set VC user limit", inline=False)
    embed.add_field(name=".vc rename <name>", value="Rename your VC", inline=False)
    embed.add_field(name=".vc transfer <member>", value="Transfer ownership of VC", inline=False)
    embed.add_field(name=".vc unmute", value="Unmute all members in VC", inline=False)
    await ctx.send(embed=embed)

# ---------- JOIN TO CREATE HANDLER ----------
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot or member.guild.id not in server_setup:
        return

    guild_id = member.guild.id
    setup = server_setup[guild_id]
    join_category = get(member.guild.categories, id=setup["join_category"])

    # Leave temporary VC deletion
    if before.channel and before.channel.id in temp_vcs.get(guild_id, {}):
        vc_id = before.channel.id
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                temp_vcs[guild_id].pop(vc_id, None)
            except:
                pass

    # Join to create
    if after.channel and after.channel.category == join_category:
        if guild_id not in temp_vcs:
            temp_vcs[guild_id] = {}

        # Determine type
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(member.guild.categories, id=setup["public_category"])
            vc_name = f"{member.display_name}'s Public VC"
            perms = None
        else:
            category = get(member.guild.categories, id=setup["private_category"])
            vc_name = f"{member.display_name}'s Private VC"
            perms = {
                member.guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True)
            }

        # Check if member already has a temp VC
        for vc in category.voice_channels:
            if vc.name.startswith(member.display_name):
                await member.move_to(vc)
                return

        # Create temp VC
        temp_vc = await member.guild.create_voice_channel(vc_name, category=category, overwrites=perms)
        temp_vcs[guild_id][temp_vc.id] = True
        await member.move_to(temp_vc)

        # Delete VC when empty
        async def delete_when_empty(vc):
            while True:
                await asyncio.sleep(10)
                if len(vc.members) == 0:
                    try:
                        await vc.delete()
                        temp_vcs[guild_id].pop(vc.id, None)
                    except:
                        pass
                    break

        bot.loop.create_task(delete_when_empty(temp_vc))

# ---------- VC COMMANDS ----------
async def get_member_vc(member):
    if member.voice and member.voice.channel and member.voice.channel.id in temp_vcs.get(member.guild.id, {}):
        return member.voice.channel
    return None

@bot.command()
async def vc_lock(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.set_permissions(ctx.guild.default_role, connect=False)
    embed = discord.Embed(description=f"{SUCCESS} {vc.name} locked.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_unlock(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.set_permissions(ctx.guild.default_role, connect=True)
    embed = discord.Embed(description=f"{SUCCESS} {vc.name} unlocked.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_kick(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    if member in vc.members:
        await member.move_to(None)
        embed = discord.Embed(description=f"{SUCCESS} {member.display_name} kicked from {vc.name}.", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description=f"{FAIL} {member.display_name} is not in your VC.", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command()
async def vc_ban(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.set_permissions(member, connect=False)
    if member in vc.members:
        await member.move_to(None)
    embed = discord.Embed(description=f"{SUCCESS} {member.display_name} banned from {vc.name}.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_permit(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.set_permissions(member, connect=True)
    embed = discord.Embed(description=f"{SUCCESS} {member.display_name} can now join {vc.name}.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_limit(ctx, limit: int):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.edit(user_limit=limit)
    embed = discord.Embed(description=f"{SUCCESS} {vc.name} limit set to {limit}.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_rename(ctx, *, name: str):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.edit(name=name)
    embed = discord.Embed(description=f"{SUCCESS} VC renamed to {name}.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_transfer(ctx, member: discord.Member):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await vc.set_permissions(member, connect=True, manage_channels=True)
    await vc.set_permissions(ctx.author, manage_channels=False)
    embed = discord.Embed(description=f"{SUCCESS} Ownership transferred to {member.display_name}.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def vc_unmute(ctx):
    vc = await get_member_vc(ctx.author)
    if not vc:
        embed = discord.Embed(description=f"{FAIL} You are not in a temporary VC.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    for m in vc.members:
        await m.edit(mute=False)
    embed = discord.Embed(description=f"{SUCCESS} Everyone unmuted in {vc.name}.", color=discord.Color.green())
    await ctx.send(embed=embed)

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
