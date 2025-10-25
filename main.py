import os
import discord
from discord.ext import commands
from discord.utils import get
from flask import Flask
import threading
import asyncio

# ------------------------------
# TOKEN & INTENTS
# ------------------------------
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# ------------------------------
# CONSTANTS
# ------------------------------
SUCCESS = "<:check_markv:1431619384987615383>"
FAIL = "<:x_markv:1431619387168657479>"

JOIN_CREATE_CATEGORY = "Join to Create"
PUBLIC_CATEGORY = "Public VCs"
PRIVATE_CATEGORY = "Private VCs"
UNMUTE_CATEGORY = "Unmute VCs"

CREATE_PUBLIC_VC = "Create Public VC"
CREATE_PRIVATE_VC = "Create Private VC"

UNMUTE_VCS = ["Unmute VC 1", "Unmute VC 2"]

server_setup = {}

# ------------------------------
# BOT EVENTS
# ------------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="VC Master • .vm commands"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    print(f"Message detected: {message.content}")  # Debug check
    await bot.process_commands(message)

# ------------------------------
# COMMANDS
# ------------------------------
@bot.command(name="vmsetup", aliases=["vm setup"])
@commands.has_permissions(administrator=True)
async def vmsetup(ctx):
    guild = ctx.guild
    try:
        if guild.id in server_setup:
            await ctx.send(f"{FAIL} VM system already set up for this server.")
            return

        join_category = await guild.create_category(JOIN_CREATE_CATEGORY)
        public_category = await guild.create_category(PUBLIC_CATEGORY)
        private_category = await guild.create_category(PRIVATE_CATEGORY)
        unmute_category = await guild.create_category(UNMUTE_CATEGORY)

        await guild.create_voice_channel(CREATE_PUBLIC_VC, category=join_category)
        await guild.create_voice_channel(CREATE_PRIVATE_VC, category=join_category)

        for vc_name in UNMUTE_VCS:
            await guild.create_voice_channel(vc_name, category=unmute_category)

        server_setup[guild.id] = {
            "join_category": join_category.id,
            "public_category": public_category.id,
            "private_category": private_category.id,
            "unmute_category": unmute_category.id
        }

        embed = discord.Embed(
            title="✅ VM System Setup Complete",
            description=f"{SUCCESS} All voice categories & channels created successfully!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"{FAIL} Setup failed.\nError: {e}")


@bot.command(name="vmreset", aliases=["vm reset"])
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    try:
        if guild.id not in server_setup:
            await ctx.send(f"{FAIL} VM system not set up.")
            return

        setup = server_setup[guild.id]
        for cat_id in setup.values():
            category = get(guild.categories, id=cat_id)
            if category:
                for ch in category.channels:
                    await ch.delete()
                await category.delete()

        del server_setup[guild.id]

        embed = discord.Embed(
            title="🧹 VM System Reset",
            description=f"{SUCCESS} All VM categories and channels deleted.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"{FAIL} Reset failed.\nError: {e}")


@bot.command(name="vmcommands", aliases=["vm commands"])
async def vmcommands(ctx):
    embed = discord.Embed(title="🎛️ VM Commands", color=discord.Color.blue())
    embed.add_field(name=".vm setup", value="Set up the VM system (Admin only)", inline=False)
    embed.add_field(name=".vm reset", value="Reset the VM system (Admin only)", inline=False)
    embed.add_field(name="Join VC", value="Join 'Create Public VC' or 'Create Private VC' to make your own.", inline=False)
    embed.set_footer(text="VC Master • Auto Voice System")
    await ctx.send(embed=embed)

# ------------------------------
# VC AUTO-CREATION SYSTEM
# ------------------------------
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
        # Determine VC type
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"{member.name}'s Public VC"
        elif after.channel.name == CREATE_PRIVATE_VC:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"{member.name}'s Private VC"
        else:
            return

        temp_vc = await guild.create_voice_channel(vc_name, category=category)
        await member.move_to(temp_vc)

        # Private VC permissions
        if category.id == setup["private_category"]:
            await temp_vc.set_permissions(guild.default_role, connect=False)
            await temp_vc.set_permissions(member, connect=True)

        async def delete_when_empty():
            await asyncio.sleep(10)
            while True:
                if len(temp_vc.members) == 0:
                    await temp_vc.delete()
                    break
                await asyncio.sleep(10)

        bot.loop.create_task(delete_when_empty())

# ------------------------------
# FLASK KEEPALIVE
# ------------------------------
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    thread = threading.Thread(target=run)
    thread.start()

keep_alive()
bot.run(TOKEN)
