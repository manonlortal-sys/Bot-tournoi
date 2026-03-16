# main.py
import os
import discord
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ======= Chargement des variables =======
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))  # facultatif pour sync rapide
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", 0))  # ID du rôle Admin Discord

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

# ======= Modal pour la commande /pari =======
class PariModal(ui.Modal, title="Créer un pari"):
    montant = ui.TextInput(label="Montant misé (K)", placeholder="50", required=True)
    cote_winamax = ui.TextInput(label="Côte Winamax", placeholder="3.2", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # Vérification rôle Admin
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ Tu n’es pas autorisé.", ephemeral=True)
            return

        # Conversion des valeurs
        try:
            mise = float(self.montant.value)
            cote_win = float(self.cote_winamax.value)
        except ValueError:
            await interaction.response.send_message("❌ Valeurs invalides.", ephemeral=True)
            return

        # Calcul
        cote_kamazone = round(cote_win * 0.8, 2)
        gain = round(mise * cote_kamazone, 2)

        # Création de l'embed
        embed = discord.Embed(title="🎰 PARI SPORTIF", color=0xFFD700)
        embed.add_field(name="💰 Mise", value=f"{mise} K", inline=False)
        embed.add_field(name="📊 Côte Winamax", value=f"{cote_win}", inline=True)
        embed.add_field(name="📉 Côte Kamazone", value=f"{cote_kamazone}", inline=True)
        embed.add_field(name="🏆 Gain potentiel", value=f"{gain} K", inline=False)

        # Envoi public
        await interaction.response.send_message(embed=embed, ephemeral=False)

# ======= Commande Slash =======
@bot.tree.command(name="pari", description="Créer un pari sportif")
async def pari(interaction: discord.Interaction):
    # Vérification rôle Admin
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ Tu n’es pas autorisé.", ephemeral=True)
        return

    # Affiche le modal
    modal = PariModal()
    await interaction.response.send_modal(modal)

# ======= Démarrage =======
@bot.event
async def on_ready():
    print(f"{bot.user} est en ligne !")
    try:
        if GUILD_ID != 0:
            guild = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild)
            print(f"Commandes slash synchronisées sur le serveur : {len(synced)}")
        else:
            synced = await bot.tree.sync()
            print(f"Commandes slash synchronisées globalement : {len(synced)}")
    except Exception as e:
        print(f"Erreur sync commandes : {e}")

if __name__ == "__main__":
    # Lance Flask en parallèle pour Render
    Thread(target=run_flask).start()
    bot.run(TOKEN)
