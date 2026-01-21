# tournoi.py
# VERSION DE RÉFÉRENCE — COMPLÈTE
# Toutes les fonctionnalités + toutes les corrections demandées
# Ne pas tronquer ce fichier

import asyncio
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

import config
import permissions
import embeds
from state import STATE, Player, Team, Match

PARIS_TZ = ZoneInfo("Europe/Paris")

ORGA_IDS = {
    config.ORGA_USER_ID,
    1352575142668013588,
}

# -------------------------------------------------
# Utils
# -------------------------------------------------
def _find_team(team_id: int) -> Team | None:
    return next((t for t in STATE.teams if t.id == team_id), None)

def _alive_teams() -> list[Team]:
    return [t for t in STATE.teams if not t.eliminated]

def _channel_mentions_for_match(team1: Team, team2: Team) -> str:
    ids = [
        team1.players[0].user_id,
        team1.players[1].user_id,
        team2.players[0].user_id,
        team2.players[1].user_id,
    ]
    return " ".join(f"<@{i}>" for i in ids)

def _match_datetime(date_str: str, time_str: str) -> datetime | None:
    try:
        ts = time_str.lower().replace("h", ":")
        hh, mm = ts.split(":")
        parts = date_str.split("/")
        if len(parts) == 2:
            day, month = map(int, parts)
            year = datetime.now(PARIS_TZ).year
        else:
            day, month, year = map(int, parts)
        return datetime(year, month, day, int(hh), int(mm), tzinfo=PARIS_TZ)
    except:
        return None

def _valid_team(p1: Player, p2: Player) -> bool:
    return p1.cls and p2.cls and p1.cls != p2.cls

# -------------------------------------------------
# Views
# -------------------------------------------------
class MatchView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id

    def _get_match(self) -> Match | None:
        return next((m for m in STATE.matches if m.id == self.match_id), None)

    def _is_player(self, user_id: int, m: Match) -> bool:
        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)
        if not t1 or not t2:
            return False
        return user_id in {
            t1.players[0].user_id,
            t1.players[1].user_id,
            t2.players[0].user_id,
            t2.players[1].user_id,
        }

    @discord.ui.button(label="INDISPONIBLE", emoji=config.EMOJI_CROSS, style=discord.ButtonStyle.danger)
    async def indispo(self, interaction: discord.Interaction, button: discord.ui.Button):
        m = self._get_match()
        if not m or m.status == "DONE":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        if not self._is_player(interaction.user.id, m):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m.status = "WAITING_AVAIL"
        m.thumbs.clear()

        orga_mentions = " ".join(f"<@{oid}>" for oid in ORGA_IDS)

        await interaction.response.send_message(
            f"{config.EMOJI_CROSS} **INDISPONIBLE**\n\n"
            f"{interaction.user.mention} n’est pas disponible.\n\n"
            "👉 Indique tes dispos alternatives.\n\n"
            f"🔔 {orga_mentions}",
            ephemeral=False
        )

        await _refresh_all_embeds(interaction.client)

    @discord.ui.button(label="VALIDER", emoji=config.EMOJI_VALIDATE, style=discord.ButtonStyle.success)
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = self._get_match()
        if not m or m.status == "DONE":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        if not m.map_name:
            picked = random.choice(config.MAPS)
            m.map_name = picked["name"]
            m.map_image = picked["image"]

        m.status = "VALIDATED"

        await _refresh_match_message(interaction.client, m)
        await _refresh_all_embeds(interaction.client)

        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)

        await interaction.channel.send(
            f"{_channel_mentions_for_match(t1, t2)}\n\n"
            f"{config.EMOJI_VALIDATE} **MATCH VALIDÉ**\n"
            f"📅 {m.date_str} à {m.time_str}\n"
            f"🗺️ **Map officielle : {m.map_name}**\n\n"
            "📸 **Merci d’envoyer le screen du résultat ici.**"
        )

        if m.map_image:
            await interaction.channel.send(m.map_image)

        await interaction.response.send_message("OK", ephemeral=True)

    @discord.ui.button(label="FORFAIT", emoji=config.EMOJI_FORFAIT, style=discord.ButtonStyle.secondary)
    async def forfait(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = self._get_match()
        if not m or m.status != "VALIDATED":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)

        await interaction.response.send_message(
            "Quelle équipe déclare forfait ?",
            view=ForfeitChoiceView(m.id, t1.id, t2.id),
            ephemeral=True
        )

class ForfeitChoiceView(discord.ui.View):
    def __init__(self, match_id: int, team1_id: int, team2_id: int):
        super().__init__(timeout=60)
        self.match_id = match_id
        self.team1_id = team1_id
        self.team2_id = team2_id

        self.add_item(ForfeitButton(team1_id))
        self.add_item(ForfeitButton(team2_id))

class ForfeitButton(discord.ui.Button):
    def __init__(self, team_id: int):
        super().__init__(
            label=f"EQUIPE {team_id}",
            style=discord.ButtonStyle.danger
        )
        self.team_id = team_id

    async def callback(self, interaction: discord.Interaction):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = next((x for x in STATE.matches if x.id == interaction.view.match_id), None)
        if not m or m.status != "VALIDATED":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        winner = m.team1_id if self.team_id == m.team2_id else m.team2_id
        m.winner_team_id = winner
        m.status = "DONE"

        loser = _find_team(self.team_id)
        if loser:
            loser.eliminated = True
            loser.eliminated_round = m.round_no

        await _refresh_match_message(interaction.client, m)
        await _refresh_all_embeds(interaction.client)

        await interaction.response.send_message(
            f"Forfait enregistré. **EQUIPE {winner} gagne.**",
            ephemeral=True
        )

# -------------------------------------------------
# Embeds refresh
# -------------------------------------------------
async def _refresh_match_message(bot: discord.Client, m: Match):
    if not m.created_message_id:
        return
    ch = await bot.fetch_channel(m.channel_id)
    msg = await ch.fetch_message(m.created_message_id)
    await msg.edit(
        embed=embeds.embed_match(m, _find_team(m.team1_id), _find_team(m.team2_id)),
        view=MatchView(m.id),
    )

async def _ensure_main_embeds(bot: discord.Client):
    ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
    if STATE.embeds.teams_msg_id is None:
        STATE.embeds.teams_msg_id = (await ch.send(embed=embeds.embed_teams(STATE.teams))).id
    if STATE.embeds.upcoming_msg_id is None:
        STATE.embeds.upcoming_msg_id = (await ch.send(embed=embeds.embed_upcoming(STATE.matches))).id
    if STATE.embeds.history_msg_id is None:
        STATE.embeds.history_msg_id = (await ch.send(embed=embeds.embed_history(STATE.matches))).id

async def _refresh_all_embeds(bot: discord.Client):
    await _ensure_main_embeds(bot)
    ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
    await (await ch.fetch_message(STATE.embeds.teams_msg_id)).edit(embed=embeds.embed_teams(STATE.teams))
    await (await ch.fetch_message(STATE.embeds.upcoming_msg_id)).edit(embed=embeds.embed_upcoming(STATE.matches))
    await (await ch.fetch_message(STATE.embeds.history_msg_id)).edit(embed=embeds.embed_history(STATE.matches))

# -------------------------------------------------
# Reminder loop
# -------------------------------------------------
async def _reminder_loop(bot: discord.Client):
    while True:
        try:
            now = datetime.now(PARIS_TZ)
            for m in STATE.matches:
                if m.status != "VALIDATED":
                    continue
                dt = _match_datetime(m.date_str, m.time_str)
                if not dt:
                    continue
                if timedelta(minutes=29) <= dt - now <= timedelta(minutes=30):
                    ch = await bot.fetch_channel(m.channel_id)
                    t1 = _find_team(m.team1_id)
                    t2 = _find_team(m.team2_id)
                    await ch.send(
                        f"{_channel_mentions_for_match(t1, t2)}\n\n"
                        "⏰ **Rappel : match dans 30 minutes**\n"
                        "📸 Pensez au screen du résultat."
                    )
        except:
            pass
        await asyncio.sleep(60)

# -------------------------------------------------
# Commands
# -------------------------------------------------
def setup(tree: app_commands.CommandTree, bot: commands.Bot):

    @tree.command(name="inscription")
    async def inscription(interaction: discord.Interaction, joueur: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        if any(p.user_id == joueur.id for p in STATE.players):
            return await interaction.followup.send("Déjà inscrit.")
        STATE.players.append(Player(user_id=joueur.id))
        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        if STATE.embeds.players_msg_id is None:
            STATE.embeds.players_msg_id = (await ch.send(embed=embeds.embed_players(STATE.players))).id
        else:
            await (await ch.fetch_message(STATE.embeds.players_msg_id)).edit(embed=embeds.embed_players(STATE.players))
        await interaction.followup.send("Joueur inscrit.")

    @tree.command(name="classe")
    async def classe(interaction: discord.Interaction, joueur: discord.Member, classe: str):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        classe = classe.lower().strip()
        if classe not in config.CLASSES:
            return await interaction.followup.send("Classe invalide.")
        for p in STATE.players:
            if p.user_id == joueur.id:
                p.cls = classe
        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        await (await ch.fetch_message(STATE.embeds.players_msg_id)).edit(embed=embeds.embed_players(STATE.players))
        await interaction.followup.send("Classe mise à jour.")

    @tree.command(name="joueur_retirer")
    async def joueur_retirer(interaction: discord.Interaction, joueur: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        if STATE.teams:
            return await interaction.followup.send("Impossible après tirage.")
        STATE.players = [p for p in STATE.players if p.user_id != joueur.id]
        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        await (await ch.fetch_message(STATE.embeds.players_msg_id)).edit(embed=embeds.embed_players(STATE.players))
        await interaction.followup.send("Joueur retiré.")

    @tree.command(name="reset")
    async def reset(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        STATE.reset()
        await interaction.followup.send("Tournoi réinitialisé.")

    @tree.command(name="tirage")
    async def tirage(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        if not STATE.players or len(STATE.players) % 2 != 0:
            return await interaction.followup.send("Nombre de joueurs invalide.")
        if any(p.cls is None for p in STATE.players):
            return await interaction.followup.send("Classes manquantes.")

        for _ in range(100):
            random.shuffle(STATE.players)
            teams = []
            ok = True
            for i in range(0, len(STATE.players), 2):
                if not _valid_team(STATE.players[i], STATE.players[i+1]):
                    ok = False
                    break
                teams.append(Team(id=len(teams)+1, players=(STATE.players[i], STATE.players[i+1])))
            if ok:
                STATE.teams = teams
                break
        else:
            return await interaction.followup.send("Tirage impossible.")

        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        await (await ch.fetch_message(STATE.embeds.players_msg_id)).delete()
        STATE.embeds.players_msg_id = None

        await _ensure_main_embeds(bot)
        await _refresh_all_embeds(bot)
        await interaction.followup.send("Équipes créées.")

    @tree.command(name="tournoi")
    async def tournoi_cmd(interaction: discord.Interaction, date: str, heure: str):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        alive = _alive_teams()
        if not alive or len(alive) % 2 != 0:
            return await interaction.followup.send("Nombre d'équipes invalide.")
        if any(m.round_no == STATE.current_round and m.status != "DONE" for m in STATE.matches):
            return await interaction.followup.send("Round précédent non terminé.")

        STATE.current_round += 1
        guild = interaction.guild
        category = guild.get_channel(config.MATCH_CATEGORY_ID)
        random.shuffle(alive)

        for i in range(0, len(alive), 2):
            t1, t2 = alive[i], alive[i+1]
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}

            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            for oid in ORGA_IDS:
                overwrites[discord.Object(id=oid)] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            for p in (*t1.players, *t2.players):
                overwrites[discord.Object(id=p.user_id)] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            channel = await guild.create_text_channel(
                name=config.MATCH_CHANNEL_TEMPLATE.format(a=t1.id, b=t2.id),
                category=category,
                overwrites=overwrites,
            )

            match = Match(
                id=len(STATE.matches)+1,
                round_no=STATE.current_round,
                team1_id=t1.id,
                team2_id=t2.id,
                date_str=date,
                time_str=heure,
                channel_id=channel.id,
            )
            STATE.matches.append(match)

            await channel.send(_channel_mentions_for_match(t1, t2))
            msg = await channel.send(embed=embeds.embed_match(match, t1, t2), view=MatchView(match.id))
            match.created_message_id = msg.id
            await msg.add_reaction(config.EMOJI_THUMBS)

        await _refresh_all_embeds(bot)
        await interaction.followup.send("Round créé.")

    @tree.command(name="modifier")
    async def modifier(interaction: discord.Interaction, date: str, heure: str):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")
        m = next((x for x in STATE.matches if x.channel_id == interaction.channel_id and x.status != "DONE"), None)
        if not m:
            return await interaction.followup.send("Aucun match modifiable.")

        m.date_str = date
        m.time_str = heure
        m.thumbs.clear()
        m.status = "WAITING_AVAIL"

        try:
            old = await interaction.channel.fetch_message(m.created_message_id)
            await old.delete()
        except:
            pass

        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)
        msg = await interaction.channel.send(embed=embeds.embed_match(m, t1, t2), view=MatchView(m.id))
        m.created_message_id = msg.id
        await msg.add_reaction(config.EMOJI_THUMBS)

        await _refresh_all_embeds(bot)
        await interaction.followup.send("Horaire modifié.")