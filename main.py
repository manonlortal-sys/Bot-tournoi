# main.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# ======= Configuration =======
TOKEN = os.getenv("DISCORD_TOKEN")       # Token depuis l'environnement
ADMIN_ROLE_NAME = "ADMIN"                # Nom du rôle autorisé
PARIS_CHANNEL_ID = 1480960334729842788  # Salon spécifique pour doublon

# ======= Intents & Bot =======
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ======= Flask pour Render =======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Discord en ligne !"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# ======= Commande Slash /pari =======
@bot.tree.command(name="pari", description="Créer un pari sportif")
@app_commands.describe(
    joueur="Le joueur à qui s'applique le pari (mention)",
    mise="Montant misé (K)",
    cote_winamax="Côte Winamax"
)
async def pari(interaction: discord.Interaction, joueur: discord.Member, mise: float, cote_winamax: float):
    # Vérification rôle ADMIN
    if ADMIN_ROLE_NAME not in [role.name for role in interaction.user.roles]:
        await interaction.response.send_message("❌ Tu n’es pas autorisé.", ephemeral=True)
        return

    # Calculs
    cote_kamazone = round(cote_winamax * 0.8, 2)
    gain = round(mise * cote_kamazone, 2)

    # Créer l'embed avec tableau aligné
    embed = discord.Embed(title="🎰 Pari Sportif", color=0xFFD700)
    embed.add_field(
        name="\u200b",
        value=f"""```
| 🎮 Joueur        │ {joueur.display_name:<15}
| 💰 Mise (K)      │ {mise:<15}
| 🎲 Côte Winamax  │ {cote_winamax:<15}
| ⚡ Côte Kamazone │ {cote_kamazone:<15}
| 🏆 Gain Potentiel│ {gain:<15}
```""",
        inline=False
    )

    # 1️⃣ Envoi dans le salon où la commande a été faite
    await interaction.response.send_message(embed=embed)

    # 2️⃣ Envoi dans le salon spécifique (doublon)
    channel = bot.get_channel(PARIS_CHANNEL_ID)
    if channel is not None:
        await channel.send(embed=embed)
        await channel.send(content=f"Bonne chance {joueur.mention} ! 🍀")

# ======= Démarrage =======
@bot.event
async def on_ready():
    print(f"{bot.user} est en ligne !")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur sync commandes : {e}")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
