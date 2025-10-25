import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from keep_alive import keep_alive

TOKEN = os.environ.get("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)
tree = bot.tree

# --- Data Storage ---
if not os.path.exists("data.json"):
    with open("data.json", "w") as f:
        json.dump({"servers": {}}, f, indent=4)

with open("data.json", "r") as f:
    data = json.load(f)

def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

# --- Server Setup ---
async def create_vc_categories(guild):
    categories = {}
    for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
        categories[cat_name] = category
    # Join-to-create channels
    join_cat = categories["JOIN-TO-CREATE"]
    for ch_name in ["Public VC", "Private VC", "Random VC"]:
        if not discord.utils.get(guild.voice_channels, name=ch_name, category=join_cat):
            await guild.create_voice_channel(ch_name, category=join_cat)
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
    for guild in bot.guilds:
        register_server(guild)
        await create_vc_categories(guild)
    await tree.sync()
    print("Slash commands synced.")

@bot.event
async def on_guild_join(guild):
    register_server(guild)
    await create_vc_categories(guild)

# --- Join-to-Create & Unmute VC Logic ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild_id = str(member.guild.id)
    register_server(member.guild)
    guild_data = data["servers"][guild_id]

    join_cat = discord.utils.get(member.guild.categories, name=guild_data["join_to_create_category"])
    public_cat = discord.utils.get(member.guild.categories, name=guild_data["public_category"])
    private_cat = discord.utils.get(member.guild.categories, name=guild_data["private_category"])
    unmute_cat = discord.utils.get(member.guild.categories, name=guild_data["unmute_category"])

    # --- Join-to-create ---
    if after.channel and after.channel.category == join_cat:
        vc_type = "public" if "public" in after.channel.name.lower() else "private"
        target_cat = public_cat if vc_type == "public" else private_cat
        new_vc = await member.guild.create_voice_channel(f"{member.name}'s VC", category=target_cat)
        await member.move_to(new_vc)
        guild_data["vcs"][str(new_vc.id)] = {
            "owner": member.id,
            "type": vc_type,
            "original_category": target_cat.name,
            "limit": None
        }
        save_data()

    # --- Unmute ---
    if after.channel and after.channel.category == unmute_cat:
        original_vc_id = None
        for vc_id, info in guild_data["vcs"].items():
            if info["owner"] == member.id:
                original_vc_id = int(vc_id)
        if original_vc_id:
            original_vc = discord.utils.get(member.guild.voice_channels, id=original_vc_id)
            if original_vc:
                await member.move_to(original_vc)

# --- Interface Command ---
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
        color=0x0000FF  # Blue
    )
    embed.set_footer(text="**ALL COMMANDS SUPPORT PREFIX AND SLASH**")
    await ctx.send(embed=embed)

# --- VM Setup & Reset Commands ---
@bot.command()
async def vm(ctx, action=None):
    if action == "setup":
        register_server(ctx.guild)
        await create_vc_categories(ctx.guild)
        await ctx.send("<:checkv:1431397623193010257> VM setup complete!")
    elif action == "reset":
        guild_id = str(ctx.guild.id)
        if guild_id in data["servers"]:
            vcs = data["servers"][guild_id]["vcs"]
            for vc_id in list(vcs.keys()):
                vc = discord.utils.get(ctx.guild.voice_channels, id=int(vc_id))
                if vc:
                    await vc.delete()
            del data["servers"][guild_id]
            save_data()
        await ctx.send("<:checkv:1431397623193010257> VM reset complete!")
    else:
        await ctx.send("<:failv:1431396982768930929> Invalid VM command!")

# --- Slash commands ---
@tree.command(name="vm", description="Setup or reset VM")
@app_commands.describe(action="setup or reset")
async def slash_vm(interaction: discord.Interaction, action: str):
    guild = interaction.guild
    if action.lower() == "setup":
        register_server(guild)
        await create_vc_categories(guild)
        await interaction.response.send_message("<:checkv:1431397623193010257> VM setup complete!")
    elif action.lower() == "reset":
        guild_id = str(guild.id)
        if guild_id in data["servers"]:
            vcs = data["servers"][guild_id]["vcs"]
            for vc_id in list(vcs.keys()):
                vc = discord.utils.get(guild.voice_channels, id=int(vc_id))
                if vc:
                    await vc.delete()
            del data["servers"][guild_id]
            save_data()
        await interaction.response.send_message("<:checkv:1431397623193010257> VM reset complete!")
    else:
        await interaction.response.send_message("<:failv:1431396982768930929> Invalid VM command!")

# --- VC Action Commands ---
@bot.command()
async def vc(ctx, action=None, member: discord.Member=None, limit: int=None):
    guild_id = str(ctx.guild.id)
    register_server(ctx.guild)
    guild_data = data["servers"][guild_id]

    user_vc = ctx.author.voice.channel if ctx.author.voice else None
    if not user_vc or str(user_vc.id) not in guild_data["vcs"]:
        await ctx.send("<:failv:1431396982768930929> You must be in your VC!")
        return

    if action == "lock":
        await user_vc.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send("<:checkv:1431397623193010257> VC locked!")
    elif action == "unlock":
        await user_vc.set_permissions(ctx.guild.default_role, connect=True)
        await ctx.send("<:checkv:1431397623193010257> VC unlocked!")
    elif action == "kick" and member:
        await member.move_to(None)
        await ctx.send(f"<:checkv:1431397623193010257> Kicked {member.name}")
    elif action == "ban" and member:
        await user_vc.set_permissions(member, connect=False)
        await ctx.send(f"<:checkv:1431397623193010257> Banned {member.name}")
    elif action == "permit" and member:
        await user_vc.set_permissions(member, connect=True)
        await ctx.send(f"<:checkv:1431397623193010257> Permitted {member.name}")
    elif action == "limit" and limit is not None:
        await user_vc.edit(user_limit=limit)
        guild_data["vcs"][str(user_vc.id)]["limit"] = limit
        save_data()
        await ctx.send(f"<:checkv:1431397623193010257> Limit set to {limit}")
    elif action == "reset":
        await user_vc.edit(user_limit=None)
        await user_vc.set_permissions(ctx.guild.default_role, connect=True)
        guild_data["vcs"][str(user_vc.id)]["limit"] = None
        save_data()
        await ctx.send("<:checkv:1431397623193010257> Reset VC!")
    elif action == "info":
        vc_info = guild_data["vcs"].get(str(user_vc.id))
        await ctx.send(f"Owner: <@{vc_info['owner']}>\nType: {vc_info['type']}\nLimit: {vc_info['limit']}")
    elif action == "rename" and member:
        await user_vc.edit(name=str(member))
        await ctx.send(f"<:checkv:1431397623193010257> Renamed VC to {member}")
    elif action == "transfer" and member:
        guild_data["vcs"][str(user_vc.id)]["owner"] = member.id
        save_data()
        await ctx.send(f"<:checkv:1431397623193010257> Transferred ownership to {member.name}")
    else:
        await ctx.send("<:failv:1431396982768930929> Invalid command!")

# --- Slash VC Commands ---
@tree.command(name="vc", description="VC actions like lock, unlock, kick, etc.")
@app_commands.describe(action="Action to perform", member="Target member (if needed)", limit="Limit (if needed)")
async def slash_vc(interaction: discord.Interaction, action: str, member: discord.Member=None, limit: int=None):
    ctx = await bot.get_context(interaction)  # helper context
    await vc(ctx, action, member, limit)

# --- Keep alive ---
keep_alive()
bot.run(TOKEN)
