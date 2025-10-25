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
tree = bot.tree

# Load data.json
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

    # Join-to-create VC
    join_cat = discord.utils.get(member.guild.categories, name=guild_data["join_to_create_category"])
    if after.channel and after.channel.category == join_cat:
        vc_type = "public" if after.channel.name.lower() == "public" else "private"
        target_cat = discord.utils.get(member.guild.categories, name=guild_data[f"{vc_type}_category"])
        new_vc = await member.guild.create_voice_channel(f"{member.name}'s VC", category=target_cat)
        await member.move_to(new_vc)

        guild_data["vcs"][str(new_vc.id)] = {
            "owner": member.id,
            "type": vc_type,
            "original_category": target_cat.name,
            "limit": None
        }
        save_data()

    # Unmute VC
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

# --- VM Setup/Reset Commands ---
@bot.command()
async def vm(ctx, action=None):
    guild_id = str(ctx.guild.id)
    register_server(ctx.guild)
    guild_data = data["servers"][guild_id]

    if action == "setup":
        await create_vc_categories(ctx.guild)
        await ctx.send("<:checkv:1431397623193010257> VM Setup completed!")
    elif action == "reset":
        # Delete all dynamic VCs
        for vc_id in list(guild_data["vcs"].keys()):
            vc = discord.utils.get(ctx.guild.voice_channels, id=int(vc_id))
            if vc:
                await vc.delete()
        guild_data["vcs"] = {}
        save_data()
        await ctx.send("<:checkv:1431397623193010257> VM Reset completed!")
    else:
        await ctx.send("<:failv:1431396982768930929> Invalid command!")

# Slash version
@tree.command(name="vm", description="Setup or reset VM")
@app_commands.describe(action="setup or reset")
async def slash_vm(interaction: discord.Interaction, action: str):
    guild_id = str(interaction.guild.id)
    register_server(interaction.guild)
    guild_data = data["servers"][guild_id]

    if action == "setup":
        await create_vc_categories(interaction.guild)
        await interaction.response.send_message("<:checkv:1431397623193010257> VM Setup completed!")
    elif action == "reset":
        for vc_id in list(guild_data["vcs"].keys()):
            vc = discord.utils.get(interaction.guild.voice_channels, id=int(vc_id))
            if vc:
                await vc.delete()
        guild_data["vcs"] = {}
        save_data()
        await interaction.response.send_message("<:checkv:1431397623193010257> VM Reset completed!")
    else:
        await interaction.response.send_message("<:failv:1431396982768930929> Invalid command!")

# --- Interface ---
@bot.command()
async def interface(ctx):
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
        color=0x0000FF,  # Blue
    )
    embed.set_footer(text="**CUSTOM VOICE CHANNELS**")
    await ctx.send(embed=embed)

@tree.command(name="interface", description="Shows the VC interface")
async def slash_interface(interaction: discord.Interaction):
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
        color=0x0000FF,
    )
    embed.set_footer(text="**CUSTOM VOICE CHANNELS**")
    await interaction.response.send_message(embed=embed)

# --- Keep alive ---
keep_alive()
bot.run(TOKEN)
