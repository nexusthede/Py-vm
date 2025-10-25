import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from flask import Flask

# --- Keep Alive (Flask) ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is online!"

def keep_alive():
    from threading import Thread
    server = Thread(target=app.run, kwargs={"host":"0.0.0.0","port":8080})
    server.start()

# --- Bot Setup ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"servers": {}}, f, indent=4)

with open(DATA_FILE, "r") as f:
    data = json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def register_server(guild: discord.Guild):
    guild_id = str(guild.id)
    if guild_id not in data["servers"]:
        data["servers"][guild_id] = {"vcs": {}, "interface_channel": None}
        save_data()

# --- VM Setup Command ---
@bot.command(name="vm")
async def vm_command(ctx, action=None):
    guild = ctx.guild
    register_server(guild)
    guild_data = data["servers"][str(guild.id)]

    if action == "setup":
        # Create categories
        jtc_cat = await guild.create_category("🎮 Join to Create")
        unmute_cat = await guild.create_category("🔊 Unmute VC")

        # Create 3 join-to-create channels
        for i in range(1, 4):
            await guild.create_voice_channel(f"Join to Create {i}", category=jtc_cat)

        # Interface embed
        embed = discord.Embed(
            title="VC INTERFACE COMMANDS",
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
            color=discord.Color.blue()
        )
        interface = await guild.create_text_channel("vc-interface", category=jtc_cat)
        await interface.send(embed=embed)
        guild_data["interface_channel"] = interface.id
        save_data()

        await ctx.send("<:checkv:1431397623193010257> VM setup completed!")

    elif action == "reset":
        # Delete all vcs and interface
        for vc_id in list(guild_data["vcs"].keys()):
            vc = guild.get_channel(int(vc_id))
            if vc:
                await vc.delete()
            del guild_data["vcs"][vc_id]

        if guild_data.get("interface_channel"):
            ch = guild.get_channel(guild_data["interface_channel"])
            if ch:
                await ch.delete()
            guild_data["interface_channel"] = None

        save_data()
        await ctx.send("<:checkv:1431397623193010257> VM reset completed!")

# --- Slash VM ---
@tree.command(name="vm", description="Setup or reset VM system")
@app_commands.describe(action="setup or reset")
async def vm_slash(interaction: discord.Interaction, action: str):
    ctx = await bot.get_context(interaction)
    await vm_command(ctx, action)

# --- VC Command ---
@bot.command(name="vc")
async def vc_command(ctx, action=None, member: discord.Member=None, limit: int=None):
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
        if vc_info:
            await ctx.send(f"Owner: <@{vc_info['owner']}>\nType: {vc_info['type']}\nLimit: {vc_info['limit']}")
        else:
            await ctx.send("<:failv:1431396982768930929> No info available for this VC.")
    elif action == "rename" and member:
        await user_vc.edit(name=str(member))
        await ctx.send(f"<:checkv:1431397623193010257> Renamed VC to {member}")
    elif action == "transfer" and member:
        guild_data["vcs"][str(user_vc.id)]["owner"] = member.id
        save_data()
        await ctx.send(f"<:checkv:1431397623193010257> VC ownership transferred to {member}")
    else:
        await ctx.send("<:failv:1431396982768930929> Invalid action or missing member/limit!")

# --- Slash VC ---
@tree.command(name="vc", description="Manage your VC")
@app_commands.describe(action="lock/unlock/kick/ban/permit/limit/reset/info/rename/transfer", member="Member to target", limit="Limit number")
async def vc_slash(interaction: discord.Interaction, action: str, member: discord.Member=None, limit: int=None):
    ctx = await bot.get_context(interaction)
    await vc_command(ctx, action, member, limit)

# --- Bot Events ---
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

# --- Run ---
keep_alive()
bot.run(os.environ["TOKEN"])
