import os
import json
import random
from typing import Any, Dict, Optional, List

import discord
from discord.ext import commands
from discord import app_commands

import config

DATA_FILE = "tournoi.json"


# -----------------------
# JSON storage (simple)
# -----------------------
def _default_data() -> Dict[str, Any]:
    return {
        "phase": "players",
        "embeds": {"players": None, "teams": None, "upcoming": None, "history": None},
        "players": [],
        "teams": [],
    }


def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        data = _default_data()
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -----------------------
# Permissions
# -----------------------
def is_orga_or_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.id == config.ORGA_USER_ID:
        return True
    if not hasattr(interaction.user, "roles"):
        return False
    return any(getattr(r, "id", None) == config.ADMIN_ROLE_ID for r in interaction.user.roles)


# -----------------------
# Embeds builders
# -----------------------
def build_players_embed(data: Dict[str, Any]) -> discord.Embed:
    e = discord.Embed(
        title="👥 Tournoi 2v2 — Joueurs inscrits",
        description=(
            "Liste des joueurs inscrits au tournoi.\n"
            "Chaque joueur doit avoir une classe avant le tirage des équipes."
        ),
        color=discord.Color.blue(),
    )

    players: List[Dict[str, Any]] = data.get("players", [])
    if not players:
        e.add_field(name="Aucun joueur", value="—", inline=False)
        return e

    lines = []
    for p in players:
        cls = p.get("class") or "classe non définie"
        lines.append(f"<@{p['user_id']}> — {cls}")
    e.add_field(name="Joueurs", value="\n".join(lines), inline=False)
    return e


def build_teams_embed() -> discord.Embed:
    return discord.Embed(
        title="🏆 Tournoi 2v2 — Équipes inscrites",
        description="Liste des équipes engagées dans le tournoi.\n❌ = équipe éliminée",
        color=discord.Color.gold(),
    )


def build_upcoming_embed() -> discord.Embed:
    return discord.Embed(
        title="📅 Tournoi 2v2 — Matchs à venir",
        color=discord.Color.gold(),
    )


def build_history_embed() -> discord.Embed:
    return discord.Embed(
        title="📜 Tournoi 2v2 — Historique des matchs",
        color=discord.Color.gold(),
    )


# -----------------------
# Discord bot
# -----------------------
INTENTS = discord.Intents.default()
INTENTS.message_content = True  # pas requis pour slash, mais utile si tu ajoutes des triggers plus tard

bot = commands.Bot(command_prefix="!", intents=INTENTS)


async def get_embeds_channel() -> discord.TextChannel:
    ch = bot.get_channel(config.CHANNEL_EMBEDS_ID)
    if isinstance(ch, discord.TextChannel):
        return ch
    # fallback fetch (si pas en cache)
    fetched = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
    if isinstance(fetched, discord.TextChannel):
        return fetched
    raise RuntimeError("CHANNEL_EMBEDS_ID ne pointe pas vers un salon texte.")


async def ensure_players_embed(channel: discord.TextChannel, data: Dict[str, Any]) -> None:
    players_id = data["embeds"].get("players")
    if players_id is None:
        msg = await channel.send(embed=build_players_embed(data))
        data["embeds"]["players"] = msg.id
        save_data(data)
        return

    try:
        msg = await channel.fetch_message(players_id)
        await msg.edit(embed=build_players_embed(data))
    except discord.NotFound:
        # message supprimé manuellement → on le recrée
        msg = await channel.send(embed=build_players_embed(data))
        data["embeds"]["players"] = msg.id
        save_data(data)


async def delete_players_embed(channel: discord.TextChannel, data: Dict[str, Any]) -> None:
    players_id = data["embeds"].get("players")
    if not players_id:
        data["embeds"]["players"] = None
        save_data(data)
        return

    try:
        msg = await channel.fetch_message(players_id)
        await msg.delete()
    except Exception:
        pass

    data["embeds"]["players"] = None
    save_data(data)


async def create_final_embeds(channel: discord.TextChannel, data: Dict[str, Any]) -> None:
    # Teams
    if data["embeds"].get("teams") is None:
        m = await channel.send(embed=build_teams_embed())
        data["embeds"]["teams"] = m.id

    # Upcoming
    if data["embeds"].get("upcoming") is None:
        m = await channel.send(embed=build_upcoming_embed())
        data["embeds"]["upcoming"] = m.id

    # History
    if data["embeds"].get("history") is None:
        m = await channel.send(embed=build_history_embed())
        data["embeds"]["history"] = m.id

    save_data(data)


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (id={bot.user.id})")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands sync: {len(synced)}")
    except Exception as e:
        print(f"❌ Erreur sync: {e}")


# -----------------------
# Slash commands
# -----------------------
@bot.tree.command(name="inscription", description="Inscrire un joueur au tournoi")
@app_commands.describe(joueur="Joueur à inscrire")
async def inscription(interaction: discord.Interaction, joueur: discord.Member):
    if not is_orga_or_admin(interaction):
        return await interaction.response.send_message("Accès refusé.", ephemeral=True)

    data = load_data()

    if data.get("phase") != "players":
        return await interaction.response.send_message("Les inscriptions sont closes.", ephemeral=True)

    players = data.get("players", [])
    if any(p["user_id"] == joueur.id for p in players):
        return await interaction.response.send_message("Ce joueur est déjà inscrit.", ephemeral=True)

    players.append({"user_id": joueur.id, "class": None})
    data["players"] = players
    save_data(data)

    channel = await get_embeds_channel()
    await ensure_players_embed(channel, data)

    await interaction.response.send_message(f"{joueur.mention} inscrit.", ephemeral=True)


@bot.tree.command(name="classe", description="Attribuer une classe à un joueur")
@app_commands.describe(joueur="Joueur", classe="Classe (liste fermée)")
async def classe(interaction: discord.Interaction, joueur: discord.Member, classe: str):
    if not is_orga_or_admin(interaction):
        return await interaction.response.send_message("Accès refusé.", ephemeral=True)

    data = load_data()
    if data.get("phase") != "players":
        return await interaction.response.send_message("Impossible après le tirage.", ephemeral=True)

    classe = (classe or "").lower().strip()
    if classe not in config.CLASSES:
        return await interaction.response.send_message("Classe invalide.", ephemeral=True)

    found = False
    for p in data.get("players", []):
        if p["user_id"] == joueur.id:
            p["class"] = classe
            found = True
            break

    if not found:
        return await interaction.response.send_message("Joueur non inscrit.", ephemeral=True)

    save_data(data)
    channel = await get_embeds_channel()
    await ensure_players_embed(channel, data)

    await interaction.response.send_message("Classe attribuée.", ephemeral=True)


@bot.tree.command(name="tirage", description="Tirage au sort des équipes (duos)")
async def tirage(interaction: discord.Interaction):
    if not is_orga_or_admin(interaction):
        return await interaction.response.send_message("Accès refusé.", ephemeral=True)

    data = load_data()
    if data.get("phase") != "players":
        return await interaction.response.send_message("Tirage déjà effectué.", ephemeral=True)

    players = data.get("players", [])
    if len(players) == 0:
        return await interaction.response.send_message("Aucun joueur inscrit.", ephemeral=True)

    if len(players) % 2 != 0:
        return await interaction.response.send_message("Nombre de joueurs invalide (pair requis).", ephemeral=True)

    if any(p.get("class") is None for p in players):
        return await interaction.response.send_message("Tous les joueurs doivent avoir une classe.", ephemeral=True)

    # Tirage des duos
    shuffled = players[:]  # copy
    random.shuffle(shuffled)

    teams = []
    team_id = 1
    for i in range(0, len(shuffled), 2):
        teams.append(
            {
                "id": team_id,
                "players": [
                    {"user_id": shuffled[i]["user_id"], "class": shuffled[i]["class"]},
                    {"user_id": shuffled[i + 1]["user_id"], "class": shuffled[i + 1]["class"]},
                ],
                "eliminated": False,
                "eliminated_round": None,
            }
        )
        team_id += 1

    data["teams"] = teams
    data["phase"] = "teams"
    save_data(data)

    channel = await get_embeds_channel()

    # 1) Supprimer embed joueurs
    await delete_players_embed(channel, data)

    # 2) Créer les 3 embeds définitifs
    await create_final_embeds(channel, data)

    await interaction.response.send_message("Tirage effectué. Les équipes sont créées.", ephemeral=True)


# -----------------------
# Run
# -----------------------
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN manquant dans les variables d'environnement (Render).")

bot.run(token)
