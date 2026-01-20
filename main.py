import os
import threading
import discord
from discord.ext import commands

from app import app
import players
import tirage
import tournoi

# --------------------
# Flask runner
# --------------------
def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# --------------------
# Discord bot
# --------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot connecté : {bot.user}")

players.setup(bot.tree, bot)
tirage.setup(bot.tree, bot)
tournoi.setup(bot.tree, bot)

# --------------------
# Start both
# --------------------
if __name__ == "__main__":
    # Flask en background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Discord bot
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN manquant")

    bot.run(token)