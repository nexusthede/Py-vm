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

        # Embedded success message
        embed = discord.Embed(title="VM Setup", description=f"{SUCCESS} VM system successfully set up!", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="VM Setup Failed", description=f"{FAIL} Failed to set up VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    try:
        if guild.id not in server_setup:
            embed = discord.Embed(title="VM Reset", description=f"{FAIL} VM system is not set up in this server.", color=discord.Color.red())
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
        embed = discord.Embed(title="VM Reset", description=f"{SUCCESS} VM system has been reset.", color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="VM Reset Failed", description=f"{FAIL} Failed to reset VM system.\nError: {e}", color=discord.Color.red())
        await ctx.send(embed=embed)


@bot.command()
async def vmcommands(ctx):
    embed = discord.Embed(title="VM Commands", color=discord.Color.blue())
    embed.add_field(name=".vm setup", value="Setup VM system (Admin only)", inline=False)
    embed.add_field(name=".vm reset", value="Reset VM system (Admin only)", inline=False)
    embed.add_field(name="VC Master Commands", value=".vc lock | .vc unlock | .vc kick | .vc ban | .vc permit | .vc limit | .vc rename | .vc transfer | .vc unmute", inline=False)
    await ctx.send(embed=embed)


# ---------- JOIN TO CREATE & UNMUTE HANDLER ----------
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild = member.guild
    if guild.id not in server_setup:
        return

    setup = server_setup[guild.id]
    join_category = get(guild.categories, id=setup["join_category"])
    unmute_category = get(guild.categories, id=setup["unmute_category"])

    # ---- Join to Create VCs ----
    if after.channel and after.channel.category == join_category:
        if after.channel.name == CREATE_PUBLIC_VC:
            category = get(guild.categories, id=setup["public_category"])
            vc_name = f"{member.display_name}'s Public VC"
            perms = None
        elif after.channel.name == CREATE_PRIVATE_VC:
            category = get(guild.categories, id=setup["private_category"])
            vc_name = f"{member.display_name}'s Private VC"
            perms = {guild.default_role: discord.PermissionOverwrite(connect=False),
                     member: discord.PermissionOverwrite(connect=True)}
        else:
            return

        temp_vc = await guild.create_voice_channel(vc_name, category=category)
        if perms:
            await temp_vc.edit(overwrites=perms)
        await member.move_to(temp_vc)

        # Delete VC when empty
        async def delete_when_empty(vc):
            while True:
                await discord.sleep(10)
                if len(vc.members) == 0:
                    await vc.delete()
                    break

        bot.loop.create_task(delete_when_empty(temp_vc))

    # ---- Unmute VCs ----
    if after.channel and after.channel.category == unmute_category:
        for m in after.channel.members:
            try:
                await m.edit(mute=False)
            except:
                pass


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
