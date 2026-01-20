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
    ts = time_str.lower().replace("h", ":")
    try:
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


class MatchView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id

    def _get_match(self) -> Match | None:
        return next((m for m in STATE.matches if m.id == self.match_id), None)

    def _is_player_allowed(self, interaction, m: Match) -> bool:
        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)
        allowed = {
            t1.players[0].user_id, t1.players[1].user_id,
            t2.players[0].user_id, t2.players[1].user_id,
        }
        return interaction.user.id in allowed

    @discord.ui.button(label="INDISPONIBLE", emoji=config.EMOJI_CROSS, style=discord.ButtonStyle.danger)
    async def indispo(self, interaction: discord.Interaction, button: discord.ui.Button):
        m = self._get_match()
        if not m or m.status != "WAITING_AVAIL":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        if not self._is_player_allowed(interaction, m):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        orga_mentions = " ".join(f"<@{oid}>" for oid in ORGA_IDS)

        await interaction.response.send_message(
            f"{config.EMOJI_CROSS} **INDISPONIBLE**\n\n"
            f"{interaction.user.mention} n’est pas disponible à l’horaire prévu.\n\n"
            "👉 Merci d’indiquer vos disponibilités alternatives dans ce canal.\n\n"
            f"🔔 Organisateurs : {orga_mentions}",
            ephemeral=False
        )

        await _refresh_all_embeds(interaction.client)

    @discord.ui.button(label="VALIDER", emoji=config.EMOJI_VALIDATE, style=discord.ButtonStyle.success)
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = self._get_match()
        if not m or m.status != "NEED_ORGA_VALIDATE":
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
            f"🗺️ {m.map_name}\n\n"
            "Merci de poster le screen du résultat."
        )

        await interaction.response.send_message("Match validé.", ephemeral=True)

    @discord.ui.button(label="FORFAIT", emoji=config.EMOJI_FORFAIT, style=discord.ButtonStyle.secondary)
    async def forfait(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = self._get_match()
        if not m or m.status != "VALIDATED":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        await interaction.response.send_message(
            "Quelle équipe déclare forfait ?",
            view=ForfeitChoiceView(self.match_id),
            ephemeral=True
        )


class ForfeitChoiceView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=60)
        self.match_id = match_id

    async def _apply(self, interaction, forfeiting_team_id: int):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        if not m or m.status != "VALIDATED":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        winner = m.team1_id if forfeiting_team_id == m.team2_id else m.team2_id
        m.winner_team_id = winner
        m.status = "DONE"

        loser = _find_team(forfeiting_team_id)
        if loser:
            loser.eliminated = True
            loser.eliminated_round = m.round_no

        await _refresh_match_message(interaction.client, m)
        await _refresh_all_embeds(interaction.client)
        await interaction.response.send_message(f"Forfait enregistré. Gagnant : EQUIPE {winner}.", ephemeral=True)

    @discord.ui.button(label="EQUIPE 1", style=discord.ButtonStyle.danger)
    async def team1(self, interaction, button):
        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        await self._apply(interaction, m.team1_id)

    @discord.ui.button(label="EQUIPE 2", style=discord.ButtonStyle.danger)
    async def team2(self, interaction, button):
        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        await self._apply(interaction, m.team2_id)


async def _refresh_match_message(bot: discord.Client, m: Match):
    if not m.created_message_id:
        return
    ch = await bot.fetch_channel(m.channel_id)
    msg = await ch.fetch_message(m.created_message_id)
    await msg.edit(embed=embeds.embed_match(m, _find_team(m.team1_id), _find_team(m.team2_id)), view=MatchView(m.id))


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
                        "⏰ **Rappel : match dans 30 minutes**"
                    )
        except:
            pass
        await asyncio.sleep(60)