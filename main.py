import os
import threading
import discord
from discord.ext import commands

from app import app
import players
import tournoi

# ---- FLASK THREAD ----
def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask, daemon=True).start()

# ---- DISCORD BOT ----
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot Discord prêt.")

players.setup(bot.tree, bot)
tournoi.setup(bot.tree, bot)

token = os.getenv("DISCORD_TOKEN")
bot.run(token)