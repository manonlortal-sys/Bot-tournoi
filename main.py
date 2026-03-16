# main.py
import os
import discord
from discord import ui
from discord.ext import commands
from flask import Flask
from threading import Thread

# ======= Configuration =======
TOKEN = os.getenv("DISCORD_TOKEN")       # Token depuis l'environnement
ADMIN_ROLE_ID =  1480944167348605031     # ID du rôle Admin Discord
PARIS_CHANNEL_ID = 1480960334729842788   # Salon spécifique pour duplication

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
        # Vérification rôle Admin
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
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

        # Créer le “tableau” dans un bloc code
        tableau = f"""```
| Joueur      | Mise (K) | Côte Winamax | Côte Kamazone | Gain Potentiel |
|------------|-----------|--------------|---------------|----------------|
| {joueur_member.display_name:<11} | {mise:<9} | {cote_win:<12} | {cote_kamazone:<13} | {gain:<14} |
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
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ Tu n’es pas autorisé.", ephemeral=True)
        return

    modal = PariModal()
    await interaction.response.send_modal(modal)

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
