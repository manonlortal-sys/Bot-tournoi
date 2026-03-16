# main.py
import os
import discord
from discord import ui
from discord.ext import commands
from flask import Flask
from threading import Thread

# ======= Configuration =======
TOKEN = os.getenv("DISCORD_TOKEN")       # Token depuis l'environnement
ADMIN_ID = 1480944167348605031           # ID de l'admin
PARIS_CHANNEL_ID = 1480960334729842788   # Salon spécifique pour doublon

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
    joueur = ui.TextInput(label="Joueur (@mention)", placeholder="@Pseudo", required=True)
    montant = ui.TextInput(label="Montant misé (K)", placeholder="50", required=True)
    cote_winamax = ui.TextInput(label="Côte Winamax", placeholder="3.2", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # Vérification ID admin
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("❌ Tu n’es pas autorisé.", ephemeral=True)
            return

        # Conversion et calcul
        try:
            mise = float(self.montant.value)
            cote_win = float(self.cote_winamax.value)
        except ValueError:
            await interaction.response.send_message("❌ Valeurs invalides.", ephemeral=True)
            return

        cote_kamazone = round(cote_win * 0.8, 2)
        gain = round(mise * cote_kamazone, 2)

        # Récupérer l'utilisateur mentionné
        try:
            user_id = int(self.joueur.value.strip("<@!>"))  # transforme la mention en ID
            joueur_member = await bot.fetch_user(user_id)
        except:
            await interaction.response.send_message("❌ Mention invalide.", ephemeral=True)
            return

        # Créer le tableau vertical en bloc code
        tableau = f"""```
| Catégorie      | Valeur           |
|----------------|-----------------|
| Joueur         | {joueur_member.display_name:<15} |
| Mise (K)       | {mise:<15} |
| Côte Winamax   | {cote_win:<15} |
| Côte Kamazone  | {cote_kamazone:<15} |
| Gain Potentiel | {gain:<15} |
```"""

        # 1️⃣ Envoi dans le salon où la commande a été faite
        await interaction.response.send_message(content=tableau)

        # 2️⃣ Envoi dans le salon spécifique (doublon)
        channel = bot.get_channel(PARIS_CHANNEL_ID)
        if channel is not None:
            await channel.send(content=tableau)
            # 3️⃣ Message mention joueur et bonne chance
            await channel.send(content=f"Bonne chance {joueur_member.mention} ! 🍀")

# ======= Commande Slash =======
@bot.tree.command(name="pari", description="Créer un pari sportif")
async def pari(interaction: discord.Interaction):
    # Vérification ID admin
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Tu n’es pas autorisé.", ephemeral=True)
        return

    modal = PariModal()
    await interaction.response.send_modal(modal)

# ======= Démarrage =======
@bot.event
async def on_ready():
    print(f"{bot.user} est en ligne !")
    try:
        synced = await bot.tree.sync()  # commandes globales
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur sync commandes : {e}")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
