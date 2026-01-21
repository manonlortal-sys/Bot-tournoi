import os
import threading

import discord
from discord.ext import commands
from flask import Flask

import tournoi

# -------------------------
# Flask (keep-alive Render)
# -------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot tournoi actif", 200


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# -------------------------
# Discord bot
# -------------------------
intents = discord.Intents.default()
intents.message_content = True  # requis pour détecter les screens (attachments)


class TournamentBot(commands.Bot):
    async def setup_hook(self):
        # Sync des slash commands
        await self.tree.sync()

        # Lancement de la boucle de rappel 30 minutes
        self.loop.create_task(tournoi._reminder_loop(self))


bot = TournamentBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot prêt : {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    from state import STATE
    import tournoi as tour_mod
    import config as cfg

    # Détection d'un screen de résultat dans un salon de match validé
    m = next(
        (x for x in STATE.matches if x.channel_id == message.channel.id and x.status == "VALIDATED"),
        None
    )
    if not m:
        return

    has_image = any(
        att.content_type and att.content_type.startswith("image/")
        for att in message.attachments
    )
    if not has_image:
        return

    t1 = tour_mod._find_team(m.team1_id)
    t2 = tour_mod._find_team(m.team2_id)
    if not t1 or not t2:
        return

    # Message de sélection du gagnant (orga/admin uniquement)
    view = tour_mod.ResultView(m.id)
    await message.channel.send(
        f"{cfg.EMOJI_TROPHY} **Résultat détecté**\n"
        f"Match **EQUIPE {m.team1_id}** vs **EQUIPE {m.team2_id}**\n\n"
        "👉 Organisateur : sélectionne l’équipe gagnante ci-dessous.",
        view=view
    )


# -------------------------
# Enregistrement des commandes tournoi
# -------------------------
tournoi.setup(bot.tree, bot)


# -------------------------
# Lancement
# -------------------------
def main():
    # Flask en thread séparé
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN manquant")

    bot.run(token)


if __name__ == "__main__":
    main()