import discord
from discord.ext import commands, tasks
import json
from keep_alive import keep_alive

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)

# Load data for multiple servers
try:
    with open("data.json") as f:
        server_data = json.load(f)
except:
    server_data = {}

# Emojis
emojis = {
    "lock": "<:lockv:1431214489981812778>",
    "unlock": "<:unlockv:1431214488316674128>",
    "kick": "<:kickv:1431213595986755725>",
    "ban": "<:banv:1431213597966598244>",
    "permit": "<:permitv:1431213599774478407>",
    "limit": "<:limitv:1431213601787744367>",
    "reset": "<:resetv:1431213603536506890>",
    "info": "<:infov:1431213604895719565>",
    "rename": "<:renamev:1431213607814828113>",
    "transfer": "<:transferv:1431213610348183582>",
    "dash": "<:dashv:1431213611858002010>"
}

# --- Utility functions ---
def save_data():
    with open("data.json", "w") as f:
        json.dump(server_data, f, indent=4)

# --- Join-to-create setup ---
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel:
        guild_id = str(member.guild.id)
        if guild_id not in server_data:
            server_data[guild_id] = {}
        # Create private/public VC based on the join-to-create channel
        jtc_channels = [ "Join Public VC", "Join Private VC", "Join Random VC" ]
        if after.channel.name in jtc_channels:
            # Determine category
            if "Public" in after.channel.name:
                category_name = "Public VCs"
            else:
                category_name = "Private VCs"

            category = discord.utils.get(member.guild.categories, name=category_name)
            if not category:
                category = await member.guild.create_category(category_name)

            # Create VC
            vc_name = f"{member.display_name}'s VC"
            vc = await member.guild.create_voice_channel(vc_name, category=category)
            await member.move_to(vc)
            # Save original VC
            server_data[guild_id][str(member.id)] = {"vc_id": vc.id, "original_vc": after.channel.id}
            save_data()

# --- Unmute category ---
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.category and after.channel.category.name == "Unmute Yourself":
        guild_id = str(member.guild.id)
        if guild_id in server_data and str(member.id) in server_data[guild_id]:
            original_vc_id = server_data[guild_id][str(member.id)]["original_vc"]
            original_vc = member.guild.get_channel(original_vc_id)
            if original_vc:
                await member.move_to(original_vc)

# --- VC commands ---
@bot.group(invoke_without_command=True)
async def vc(ctx):
    await ctx.send("Available subcommands: lock, unlock, kick, ban, permit, limit, reset, info, rename, transfer")

@vc.command()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, connect=False)
    await ctx.send(f"{emojis['lock']} VC locked!")

@vc.command()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, connect=True)
    await ctx.send(f"{emojis['unlock']} VC unlocked!")

# Add other commands similarly (kick, ban, permit, limit, reset, info, rename, transfer)...

# --- Interface ---
@bot.command()
async def interface(ctx):
    embed = discord.Embed(
        title="**EDIT YOUR VC BY USING THE BUTTONS BELOW:**",
        description=(
            f"`{emojis['lock']} VC lock - Locks the VC`\n"
            f"`{emojis['unlock']} VC unlock - Unlocks the VC`\n"
            f"`{emojis['kick']} VC kick - Kicks a user from the VC`\n"
            f"`{emojis['ban']} VC ban - Bans a user from the VC`\n"
            f"`{emojis['permit']} VC permit - Permits a user to the VC`\n"
            f"`{emojis['limit']} VC limit - Changes the VC limit`\n"
            f"`{emojis['reset']} VC reset - Resets the VC limit and perms`\n"
            f"`{emojis['info']} VC info - Shows info about the VC`\n"
            f"`{emojis['rename']} VC rename - Changes the VC name`\n"
            f"`{emojis['transfer']} VC transfer - Transfers the VC ownership`"
        ),
        color=0x32CD32  # Lime color
    )

    view = discord.ui.View()
    for key in ["lock","unlock","kick","ban","permit","limit","reset","info","rename","transfer"]:
        button = discord.ui.Button(label=key.upper(), emoji=emojis[key], style=discord.ButtonStyle.secondary)
        view.add_item(button)

    await ctx.send(embed=embed, view=view)

# --- Run bot ---
keep_alive()
bot.run("YOUR_DISCORD_BOT_TOKEN")
