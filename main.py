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

# Keep track of server setup and temp VCs
server_setup = {}
temp_vcs = {}

# ---------- BOT COMMANDS ----------

@bot.command()
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

        embed = discord.Embed(title="VM System", description=f"{SUCCESS} VM system successfully set up!", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="VM System Error", description=f"{FAIL} Failed to set up VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

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
        embed = discord.Embed(title="VM System", description=f"{SUCCESS} VM system has been reset.", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="VM System Error", description=f"{FAIL} Failed to reset VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command()
async def vmcommands(ctx):
    embed = discord.Embed(title="VM Master Commands", color=discord.Color.blue())
    embed.add_field(name=".vmsetup", value="Setup VM system (Admin only)", inline=False)
    embed.add_field(name=".vmreset", value="Reset VM system (Admin only)", inline=False)
    embed.add_field(name="VC Master", value="Join Public/Private VC to create your own temporary VC", inline=False)
    embed.add_field(name=".vc lock", value="Lock your VC", inline=False)
    embed.add_field(name=".vc unlock", value="Unlock your VC", inline=False)
    embed.add_field(name=".vc kick", value="Kick member from your VC", inline=False)
    embed.add_field(name=".vc ban", value="Ban member from your VC", inline=False)
    embed.add_field(name=".vc permit", value="Allow member to join your VC", inline=False)
    embed.add_field(name=".vc limit", value="Set user limit of your VC", inline=False)
    embed.add_field(name=".vc rename", value="Rename your VC", inline=False)
    embed.add_field(name=".vc transfer", value="Transfer ownership of VC", inline=False)
    embed.add_field(name=".vc unmute", value="Unmute everyone in your VC", inline=False)
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
        # Determine type
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"{member.display_name}'s channel"
            perms = None
        else:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"{member.display_name}'s channel"
            perms = {guild.default_role: discord.PermissionOverwrite(connect=False),
                     member: discord.PermissionOverwrite(connect=True)}

        # Create temp VC
        if perms:
            temp_vc = await guild.create_voice_channel(vc_name, category=category, overwrites=perms)
        else:
            temp_vc = await guild.create_voice_channel(vc_name, category=category)

        await member.move_to(temp_vc)

        # Track VC owner
        temp_vcs[temp_vc.id] = member.id

        # Delete VC when empty
        async def delete_when_empty(vc):
            while True:
                await asyncio.sleep(10)
                if len(vc.members) == 0:
                    temp_vcs.pop(vc.id, None)
                    await vc.delete()
                    break

        bot.loop.create_task(delete_when_empty(temp_vc))

# ---------- VC MASTER COMMANDS ----------
@bot.group()
async def vc(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"{FAIL} Invalid VC command. Use `.vmcommands` to see all.")

@vc.command()
async def lock(ctx):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await vc.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send(f"{SUCCESS} VC locked!")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def unlock(ctx):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await vc.set_permissions(ctx.guild.default_role, connect=True)
        await ctx.send(f"{SUCCESS} VC unlocked!")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def kick(ctx, member: discord.Member):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await member.move_to(None)
        await ctx.send(f"{SUCCESS} Kicked {member.display_name} from VC.")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def ban(ctx, member: discord.Member):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await vc.set_permissions(member, connect=False)
        await member.move_to(None)
        await ctx.send(f"{SUCCESS} Banned {member.display_name} from VC.")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def permit(ctx, member: discord.Member):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await vc.set_permissions(member, connect=True)
        await ctx.send(f"{SUCCESS} Permitted {member.display_name} to join VC.")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def limit(ctx, limit: int):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await vc.edit(user_limit=limit)
        await ctx.send(f"{SUCCESS} VC user limit set to {limit}.")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def rename(ctx, *, name):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        await vc.edit(name=f"{ctx.author.display_name}'s {name}")
        await ctx.send(f"{SUCCESS} VC renamed!")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def transfer(ctx, member: discord.Member):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        temp_vcs[vc.id] = member.id
        await ctx.send(f"{SUCCESS} VC ownership transferred to {member.display_name}.")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

@vc.command()
async def unmute(ctx):
    vc = ctx.author.voice.channel
    if vc and temp_vcs.get(vc.id) == ctx.author.id:
        for m in vc.members:
            await m.edit(mute=False)
        await ctx.send(f"{SUCCESS} Everyone has been unmuted!")
    else:
        await ctx.send(f"{FAIL} You don't own this VC!")

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
