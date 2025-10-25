import os
import discord
from discord.ext import commands
from discord.utils import get
from flask import Flask
import threading

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

# Categories & Channels
JOIN_CREATE_CATEGORY = "Join to Create"
PUBLIC_CATEGORY = "Public VCs"
PRIVATE_CATEGORY = "Private VCs"
UNMUTE_CATEGORY = "Unmute VCs"

CREATE_PUBLIC_VC = "Create Public VC"
CREATE_PRIVATE_VC = "Create Private VC"

UNMUTE_VCS = ["Unmute VC 1", "Unmute VC 2"]

# Track setup per server
server_setup = {}

# ---------- BOT COMMANDS ----------

@bot.command()
@commands.has_permissions(administrator=True)
async def vmsetup(ctx):
    guild = ctx.guild
    if guild.id in server_setup:
        await ctx.send(embed=discord.Embed(
            description=f"{FAIL} VM system already set up for this server.",
            color=discord.Color.red()
        ))
        return

    try:
        # Create categories
        join_cat = await guild.create_category(JOIN_CREATE_CATEGORY)
        public_cat = await guild.create_category(PUBLIC_CATEGORY)
        private_cat = await guild.create_category(PRIVATE_CATEGORY)
        unmute_cat = await guild.create_category(UNMUTE_CATEGORY)

        # Create join-to-create VCs
        await guild.create_voice_channel(CREATE_PUBLIC_VC, category=join_cat)
        await guild.create_voice_channel(CREATE_PRIVATE_VC, category=join_cat)

        # Create unmute VCs
        for name in UNMUTE_VCS:
            await guild.create_voice_channel(name, category=unmute_cat)

        # Save setup
        server_setup[guild.id] = {
            "join_category": join_cat.id,
            "public_category": public_cat.id,
            "private_category": private_cat.id,
            "unmute_category": unmute_cat.id
        }

        await ctx.send(embed=discord.Embed(
            description=f"{SUCCESS} VM system successfully set up!",
            color=discord.Color.green()
        ))

    except Exception as e:
        await ctx.send(embed=discord.Embed(
            description=f"{FAIL} Failed to set up VM system.\nError: {e}",
            color=discord.Color.red()
        ))


@bot.command()
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    if guild.id not in server_setup:
        await ctx.send(embed=discord.Embed(
            description=f"{FAIL} VM system is not set up in this server.",
            color=discord.Color.red()
        ))
        return

    try:
        setup = server_setup[guild.id]
        for cat_id in setup.values():
            cat = get(guild.categories, id=cat_id)
            if cat:
                for ch in cat.channels:
                    await ch.delete()
                await cat.delete()
        server_setup.pop(guild.id)

        await ctx.send(embed=discord.Embed(
            description=f"{SUCCESS} VM system has been reset.",
            color=discord.Color.green()
        ))
    except Exception as e:
        await ctx.send(embed=discord.Embed(
            description=f"{FAIL} Failed to reset VM system.\nError: {e}",
            color=discord.Color.red()
        ))


@bot.command()
async def vmcommands(ctx):
    embed = discord.Embed(title="VM Commands", color=discord.Color.blue())
    embed.add_field(name=".vm setup", value="Setup VM system (Admin only)", inline=False)
    embed.add_field(name=".vm reset", value="Reset VM system (Admin only)", inline=False)
    embed.set_footer(text="Join Public/Private VC to auto-create your temporary VC")
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
    join_cat = get(guild.categories, id=setup["join_category"])

    if after.channel and after.channel.category == join_cat:
        # Determine type
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"{member.name}'s Public VC"
            perms = {}
        else:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"{member.name}'s Private VC"
            perms = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True)
            }

        # Create temp VC
        temp_vc = await guild.create_voice_channel(vc_name, category=category, overwrites=perms)
        await member.move_to(temp_vc)

        # Delete VC when empty
        async def delete_when_empty():
            while True:
                await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=10))
                if len(temp_vc.members) == 0:
                    await temp_vc.delete()
                    break

        bot.loop.create_task(delete_when_empty())

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
