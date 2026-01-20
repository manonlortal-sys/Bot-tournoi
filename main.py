import os
import discord
from discord.ext import commands

import players
import tirage

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot connecté : {bot.user}")

players.setup(bot.tree, bot)
tirage.setup(bot.tree, bot)

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN manquant")

bot.run(token)