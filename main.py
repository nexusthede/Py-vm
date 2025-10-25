import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
bot.remove_command("help")

# Custom emojis
EMOJIS = {
    "lock": "<:lockv:1431214489981812778>",
    "unlock": "<:unlockv:1431214488316674128>",
    "kick": "<:kickv:1431213595986755725>",
    "ban": "<:banv:1431213597966598244>",
    "permit": "<:permitv:1431213599774478407>",
    "limit": "<:limitv:1431213601787744367>",
    "reset": "<:resetv:1431213603536506890>",
    "info": "<:infov:1431213604895719565>",
    "edit": "<:editv:1431213607814828113>",
    "transfer": "<:transferv:1431213610348183582>",
    "check": "<:checkv:1431397623193010257>",
    "fail": "<:failv:1431396982768930929>",
    "dash": "<:dashv:1431213611858002010>"
}

# Embed color
EMBED_COLOR = discord.Color.blue()

# Keep track of guild data
guild_data = {}

# Keep alive Flask server
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running."

def keep_alive():
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

keep_alive()

# -----------------
# Utility Functions
# -----------------
async def create_category_if_not_exists(guild, name):
    for cat in guild.categories:
        if cat.name == name:
            return cat
    return await guild.create_category(name)

async def create_vc(guild, name, category=None, temp=False):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=True)
    }
    channel = await guild.create_voice_channel(name=name, overwrites=overwrites, category=category)
    if temp:
        guild_data.setdefault(str(guild.id), {}).setdefault("temp_vcs", []).append(channel.id)
    return channel

def embed_success(title, description):
    return discord.Embed(
        title=title,
        description=f"{EMOJIS['check']} {description}",
        color=EMBED_COLOR
    )

def embed_fail(title, description):
    return discord.Embed(
        title=title,
        description=f"{EMOJIS['fail']} {description}",
        color=EMBED_COLOR
    )

# -----------------
# VM Setup Command
# -----------------
@bot.command(name="vm")
async def vm_setup(ctx, action=None):
    guild = ctx.guild
    if action == "setup":
        # Create categories
        join_cat = await create_category_if_not_exists(guild, "Join to Create")
        public_cat = await create_category_if_not_exists(guild, "Public VCs")
        priv_cat = await create_category_if_not_exists(guild, "Private VCs")
        unmute_cat = await create_category_if_not_exists(guild, "Unmute VCs")

        # Create Join-to-create channels
        for i in range(1,4):
            await create_vc(guild, f"Join VC {i}", join_cat)

        # Interface embed
        embed = discord.Embed(title="VC Interface", color=EMBED_COLOR)
        embed.description = (
            f"{EMOJIS['lock']} `vc lock` {EMOJIS['dash']} Locks the VC\n"
            f"{EMOJIS['unlock']} `vc unlock` {EMOJIS['dash']} Unlocks the VC\n"
            f"{EMOJIS['kick']} `vc kick` {EMOJIS['dash']} Kicks a user\n"
            f"{EMOJIS['ban']} `vc ban` {EMOJIS['dash']} Bans a user\n"
            f"{EMOJIS['permit']} `vc permit` {EMOJIS['dash']} Permits a user\n"
            f"{EMOJIS['limit']} `vc limit` {EMOJIS['dash']} Changes VC limit\n"
            f"{EMOJIS['reset']} `vc reset` {EMOJIS['dash']} Resets VC limit/perms\n"
            f"{EMOJIS['info']} `vc info` {EMOJIS['dash']} Shows VC info\n"
            f"{EMOJIS['edit']} `vc rename` {EMOJIS['dash']} Renames VC\n"
            f"{EMOJIS['transfer']} `vc transfer` {EMOJIS['dash']} Transfers ownership"
        )

        # Buttons
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Public VC", style=discord.ButtonStyle.green))
        view.add_item(discord.ui.Button(label="Private VC", style=discord.ButtonStyle.gray))
        view.add_item(discord.ui.Button(label="Join Random VC", style=discord.ButtonStyle.blurple))

        await ctx.send(embed=embed, view=view)
        await ctx.send(embed=embed_success("Setup Complete", "VC system has been setup!"))

    elif action == "reset":
        # Reset all data
        guild_data[str(guild.id)] = {}
        await ctx.send(embed=embed_success("Reset Complete", "VC system has been reset."))

    else:
        await ctx.send(embed=embed_fail("Invalid Command", "Use `vm setup` or `vm reset`"))

# -----------------
# Slash Commands
# -----------------
@bot.tree.command(name="vm")
@app_commands.describe(action="setup or reset the VC system")
async def vm(interaction: discord.Interaction, action: str):
    ctx = await bot.get_context(interaction.message)
    await vm_setup(ctx, action)

# -----------------
# Run Bot
# -----------------
bot.run(os.getenv("TOKEN"))
