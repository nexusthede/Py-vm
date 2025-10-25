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

# --- Data management ---
if not os.path.exists("data.json"):
    with open("data.json", "w") as f:
        json.dump({"servers": {}}, f, indent=4)

with open("data.json", "r") as f:
    data = json.load(f)

def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

def register_server(guild):
    if str(guild.id) not in data["servers"]:
        data["servers"][str(guild.id)] = {
            "join_to_create_category": None,
            "public_category": None,
            "private_category": None,
            "unmute_category": None,
            "vcs": {}
        }
        save_data()

# --- Helper functions ---
async def create_categories_and_vcs(guild):
    """Create main categories and 3 join-to-create VCs."""
    join_cat = discord.utils.get(guild.categories, name="JOIN-TO-CREATE")
    public_cat = discord.utils.get(guild.categories, name="PUBLIC VCS")
    private_cat = discord.utils.get(guild.categories, name="PRIVATE VCS")
    unmute_cat = discord.utils.get(guild.categories, name="UNMUTE")

    if not join_cat:
        join_cat = await guild.create_category("JOIN-TO-CREATE")
    if not public_cat:
        public_cat = await guild.create_category("PUBLIC VCS")
    if not private_cat:
        private_cat = await guild.create_category("PRIVATE VCS")
    if not unmute_cat:
        unmute_cat = await guild.create_category("UNMUTE")

    # Create 3 join-to-create VC channels if they don't exist
    join_vcs_names = ["Public VC", "Private VC", "Random VC"]
    for vc_name in join_vcs_names:
        if not discord.utils.get(join_cat.voice_channels, name=vc_name):
            await guild.create_voice_channel(vc_name, category=join_cat)

    # Save category info in JSON
    data["servers"][str(guild.id)]["join_to_create_category"] = join_cat.name
    data["servers"][str(guild.id)]["public_category"] = public_cat.name
    data["servers"][str(guild.id)]["private_category"] = private_cat.name
    data["servers"][str(guild.id)]["unmute_category"] = unmute_cat.name
    save_data()

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.event
async def on_guild_join(guild):
    register_server(guild)

# --- Join-to-create VC logic ---
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

    # --- Join-to-create VC ---
    if after.channel and after.channel.category == join_cat:
        # Determine type
        vc_type = "public" if "public" in after.channel.name.lower() else "private"
        target_cat = public_cat if vc_type == "public" else private_cat

        # Create new VC
        new_vc = await member.guild.create_voice_channel(f"{member.name}'s VC", category=target_cat)
        await member.move_to(new_vc)

        # Save VC info
        guild_data["vcs"][str(new_vc.id)] = {
            "owner": member.id,
            "type": vc_type,
            "original_category": target_cat.name,
            "limit": None
        }
        save_data()

    # --- Unmute VC ---
    if after.channel and after.channel.category == unmute_cat:
        original_vc_id = None
        for vc_id, info in guild_data["vcs"].items():
            if info["owner"] == member.id:
                original_vc_id = int(vc_id)
        if original_vc_id:
            original_vc = discord.utils.get(member.guild.voice_channels, id=original_vc_id)
            if original_vc:
                await member.move_to(original_vc)

# --- VM Setup / Reset commands ---
@bot.command()
async def vm(ctx, action=None):
    guild = ctx.guild
    register_server(guild)

    if action == "setup":
        await create_categories_and_vcs(guild)

        # Send interface embed
        embed = discord.Embed(
            title="**EDIT YOUR VC BY USING THE BUTTONS BELOW:**",
            description=(
                "<:lockv:1431214489981812778> `vc lock` <:dashv:1431213611858002010> Locks the VC\n"
                "<:unlockv:1431214488316674128> `vc unlock` <:dashv:1431213611858002010> Unlocks the VC\n"
                "<:kickv:1431213595986755725> `vc kick` <:dashv:1431213611858002010> Kicks a user from the VC\n"
                "<:banv:1431213597966598244> `vc ban` <:dashv:1431213611858002010> Bans a user from the VC\n"
                "<:permitv:1431213599774478407> `vc permit` <:dashv:1431213611858002010> Permits a user\n"
                "<:limitv:1431213601787744367> `vc limit` <:dashv:1431213611858002010> Changes VC limit\n"
                "<:resetv:1431213603536506890> `vc reset` <:dashv:1431213611858002010> Resets VC\n"
                "<:infov:1431213604895719565> `vc info` <:dashv:1431213611858002010> Shows VC info\n"
                "<:editv:1431213607814828113> `vc rename` <:dashv:1431213611858002010> Renames VC\n"
                "<:transferv:1431213610348183582> `vc transfer` <:dashv:1431213611858002010> Transfers VC ownership"
            ),
            color=0x0000FF
        )
        embed.set_footer(text="**USE THE BUTTONS TO EDIT YOUR VC**")
        await ctx.send(embed=embed)
        await ctx.send("<:checkv:1431397623193010257> VM setup completed!")

    elif action == "reset":
        guild_data = data["servers"][str(guild.id)]

        # Delete all VCs and categories created
        for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
            category = discord.utils.get(guild.categories, name=cat_name)
            if category:
                for vc in category.voice_channels:
                    await vc.delete()
                await category.delete()

        # Clear JSON data
        data["servers"][str(guild.id)]["vcs"] = {}
        save_data()
        await ctx.send("<:checkv:1431397623193010257> VM reset completed!")

    else:
        await ctx.send("<:failv:1431396982768930929> Invalid VM command!")

# --- Slash commands ---
@tree.command(name="vm", description="Setup or reset the VM system")
@app_commands.describe(action="setup or reset")
async def vm_slash(interaction: discord.Interaction, action: str):
    ctx_guild = interaction.guild
    register_server(ctx_guild)

    if action.lower() == "setup":
        await create_categories_and_vcs(ctx_guild)
        embed = discord.Embed(
            title="**EDIT YOUR VC BY USING THE BUTTONS BELOW:**",
            description=(
                "<:lockv:1431214489981812778> `vc lock` <:dashv:1431213611858002010> Locks the VC\n"
                "<:unlockv:1431214488316674128> `vc unlock` <:dashv:1431213611858002010> Unlocks the VC\n"
                "<:kickv:1431213595986755725> `vc kick` <:dashv:1431213611858002010> Kicks a user from the VC\n"
                "<:banv:1431213597966598244> `vc ban` <:dashv:1431213611858002010> Bans a user from the VC\n"
                "<:permitv:1431213599774478407> `vc permit` <:dashv:1431213611858002010> Permits a user\n"
                "<:limitv:1431213601787744367> `vc limit` <:dashv:1431213611858002010> Changes VC limit\n"
                "<:resetv:1431213603536506890> `vc reset` <:dashv:1431213611858002010> Resets VC\n"
                "<:infov:1431213604895719565> `vc info` <:dashv:1431213611858002010> Shows VC info\n"
                "<:editv:1431213607814828113> `vc rename` <:dashv:1431213611858002010> Renames VC\n"
                "<:transferv:1431213610348183582> `vc transfer` <:dashv:1431213611858002010> Transfers VC ownership"
            ),
            color=0x0000FF
        )
        embed.set_footer(text="**USE THE BUTTONS TO EDIT YOUR VC**")
        await interaction.response.send_message(embed=embed)

    elif action.lower() == "reset":
        guild_data = data["servers"][str(ctx_guild.id)]
        for cat_name in ["JOIN-TO-CREATE", "PUBLIC VCS", "PRIVATE VCS", "UNMUTE"]:
            category = discord.utils.get(ctx_guild.categories, name=cat_name)
            if category:
                for vc in category.voice_channels:
                    await vc.delete()
                await category.delete()
        data["servers"][str(ctx_guild.id)]["vcs"] = {}
        save_data()
        await interaction.response.send_message("<:checkv:1431397623193010257> VM reset completed!")
    else:
        await interaction.response.send_message("<:failv:1431396982768930929> Invalid VM command!")

# --- Keep bot alive ---
keep_alive()
bot.run(TOKEN)
