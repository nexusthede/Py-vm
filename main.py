import os
import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("TOKEN")  # Your bot token
PREFIX = "."  # Command prefix

SUCCESS = "<:check_markv:1431619384987615383>"
FAIL = "<:x_markv:1431619387168657479>"

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ---- UTILITY ----
async def create_category(name, guild):
    existing = discord.utils.get(guild.categories, name=name)
    if existing:
        return existing
    return await guild.create_category(name)

async def create_vc(name, category):
    existing = discord.utils.get(category.voice_channels, name=name)
    if existing:
        return existing
    return await category.create_voice_channel(name)

# ---- SETUP COMMAND ----
@bot.command()
@commands.has_permissions(administrator=True)
async def vmsetup(ctx):
    guild = ctx.guild
    try:
        join_cat = await create_category("Join to Create", guild)
        public_cat = await create_category("Public VCs", guild)
        private_cat = await create_category("Private VCs", guild)
        unmute_cat = await create_category("Unmute VCs", guild)

        # Permanent VCs in Join to Create
        await create_vc("Create Public VC", join_cat)
        await create_vc("Create Private VC", join_cat)

        # 2 Unmute VCs
        await create_vc("Unmute 1", unmute_cat)
        await create_vc("Unmute 2", unmute_cat)

        embed = discord.Embed(title="VM Setup", description=f"{SUCCESS} VM setup complete!", color=discord.Color.green())
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="VM Setup", description=f"{FAIL} Failed to setup VCs.\n{e}", color=discord.Color.red())
        await ctx.send(embed=embed)

# ---- RESET COMMAND ----
@bot.command()
@commands.has_permissions(administrator=True)
async def vmreset(ctx):
    guild = ctx.guild
    try:
        categories = ["Join to Create", "Public VCs", "Private VCs", "Unmute VCs"]
        for cat_name in categories:
            cat = discord.utils.get(guild.categories, name=cat_name)
            if cat:
                for ch in cat.channels:
                    await ch.delete()
                await cat.delete()
        embed = discord.Embed(title="VM Reset", description=f"{SUCCESS} VM reset complete!", color=discord.Color.green())
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="VM Reset", description=f"{FAIL} Failed to reset VM.\n{e}", color=discord.Color.red())
        await ctx.send(embed=embed)

# ---- COMMAND LIST ----
@bot.command()
async def vm(ctx):
    embed = discord.Embed(title="VM Commands", color=discord.Color.blue())
    embed.add_field(name=f"{PREFIX}vmsetup", value="Setup all VM categories and permanent channels", inline=False)
    embed.add_field(name=f"{PREFIX}vmreset", value="Delete all VM categories and channels", inline=False)
    await ctx.send(embed=embed)

# ---- AUTO TEMP VC CREATION ----
@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if after.channel and after.channel.category:
        cat_name = after.channel.category.name
        vc_name = after.channel.name

        # If user joins Create Public VC or Create Private VC, make temp VC
        if vc_name == "Create Public VC":
            target_cat = discord.utils.get(guild.categories, name="Public VCs")
            temp_vc = await guild.create_voice_channel(f"{member.display_name}'s VC", category=target_cat)
            await member.move_to(temp_vc)
        elif vc_name == "Create Private VC":
            target_cat = discord.utils.get(guild.categories, name="Private VCs")
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True, manage_channels=True)
            }
            temp_vc = await guild.create_voice_channel(f"{member.display_name}'s VC", overwrites=overwrites, category=target_cat)
            await member.move_to(temp_vc)

    # Delete temp VC if empty and not permanent
    if before.channel:
        if before.channel.category and before.channel.category.name in ["Public VCs", "Private VCs"]:
            if len(before.channel.members) == 0 and not before.channel.name.startswith("Create"):
                await before.channel.delete()

# ---- BOT READY ----
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---- RUN BOT ----
bot.run(TOKEN)
