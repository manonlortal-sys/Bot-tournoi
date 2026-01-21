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

# =================================================
# Utils
# =================================================

def _find_team(team_id: int) -> Team | None:
    return next((t for t in STATE.teams if t.id == team_id), None)

def _alive_teams():
    return [t for t in STATE.teams if not t.eliminated]

def _mentions(t1: Team, t2: Team):
    ids = [p.user_id for p in (*t1.players, *t2.players)]
    return " ".join(f"<@{i}>" for i in ids)

def _match_dt(date_str, time_str):
    try:
        h, m = time_str.lower().replace("h", ":").split(":")
        d = date_str.split("/")
        y = datetime.now(PARIS_TZ).year if len(d) == 2 else int(d[2])
        return datetime(y, int(d[1]), int(d[0]), int(h), int(m), tzinfo=PARIS_TZ)
    except:
        return None

def _valid_team(p1: Player, p2: Player):
    return p1.cls and p2.cls and p1.cls != p2.cls

# =================================================
# Views
# =================================================

class ResultView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id

    async def _win(self, interaction, winner_id: int):
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return

        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        if not m or m.status != "VALIDATED":
            return

        m.status = "DONE"
        m.winner_team_id = winner_id

        loser = m.team1_id if winner_id == m.team2_id else m.team2_id
        loser_team = _find_team(loser)
        if loser_team:
            loser_team.eliminated = True
            loser_team.eliminated_round = m.round_no

        ch = await interaction.client.fetch_channel(m.channel_id)
        await ch.send(f"🏆 **Victoire enregistrée : EQUIPE {winner_id}**")

        await _refresh_match_message(interaction.client, m)
        await _refresh_all_embeds(interaction.client)

    @discord.ui.button(label="EQUIPE 1", style=discord.ButtonStyle.primary)
    async def win1(self, interaction, _):
        m = next(x for x in STATE.matches if x.id == self.match_id)
        await self._win(interaction, m.team1_id)

    @discord.ui.button(label="EQUIPE 2", style=discord.ButtonStyle.primary)
    async def win2(self, interaction, _):
        m = next(x for x in STATE.matches if x.id == self.match_id)
        await self._win(interaction, m.team2_id)

class ForfeitView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id

    async def _forfeit(self, interaction, forfeiting_id):
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return

        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        if not m or m.status != "VALIDATED":
            return

        winner = m.team1_id if forfeiting_id == m.team2_id else m.team2_id
        m.status = "DONE"
        m.winner_team_id = winner

        loser = _find_team(forfeiting_id)
        if loser:
            loser.eliminated = True
            loser.eliminated_round = m.round_no

        ch = await interaction.client.fetch_channel(m.channel_id)
        await ch.send(f"🚪 **Forfait — EQUIPE {forfeiting_id}**\n🏆 Gagnant : EQUIPE {winner}")

        await _refresh_match_message(interaction.client, m)
        await _refresh_all_embeds(interaction.client)

    @discord.ui.button(label="FORFAIT EQUIPE 1", style=discord.ButtonStyle.danger)
    async def f1(self, interaction, _):
        m = next(x for x in STATE.matches if x.id == self.match_id)
        await self._forfeit(interaction, m.team1_id)

    @discord.ui.button(label="FORFAIT EQUIPE 2", style=discord.ButtonStyle.danger)
    async def f2(self, interaction, _):
        m = next(x for x in STATE.matches if x.id == self.match_id)
        await self._forfeit(interaction, m.team2_id)

class MatchView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id

    def _match(self):
        return next((m for m in STATE.matches if m.id == self.match_id), None)

    @discord.ui.button(label="INDISPONIBLE", emoji=config.EMOJI_CROSS, style=discord.ButtonStyle.danger)
    async def indispo(self, interaction, _):
        await interaction.response.defer()

        m = self._match()
        if not m or m.status == "DONE":
            return

        t1, t2 = _find_team(m.team1_id), _find_team(m.team2_id)
        players = {p.user_id for p in (*t1.players, *t2.players)}
        if interaction.user.id not in players:
            return

        m.status = "WAITING_AVAIL"
        m.thumbs.clear()

        orga_mentions = " ".join(f"<@{i}>" for i in ORGA_IDS)
        await interaction.channel.send(
            f"{config.EMOJI_CROSS} **INDISPONIBLE**\n"
            f"{interaction.user.mention} n’est pas disponible.\n"
            f"{orga_mentions}"
        )

        await _refresh_all_embeds(interaction.client)

    @discord.ui.button(label="VALIDER", emoji=config.EMOJI_VALIDATE, style=discord.ButtonStyle.success)
    async def validate(self, interaction, _):
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return

        m = self._match()
        if not m or m.status == "DONE":
            return

        picked = random.choice(config.MAPS)
        m.map_name = picked["name"]
        m.map_image = picked["image"]
        m.status = "VALIDATED"

        ch = await interaction.client.fetch_channel(m.channel_id)

        try:
            old = await ch.fetch_message(m.created_message_id)
            await old.delete()
        except:
            pass

        t1, t2 = _find_team(m.team1_id), _find_team(m.team2_id)
        msg = await ch.send(
            content=_mentions(t1, t2),
            embed=embeds.embed_match(m, t1, t2),
            view=ForfeitView(m.id)
        )
        m.created_message_id = msg.id

        await ch.send(m.map_image)
        await ch.send("📸 **Postez le screen du résultat ici.**")

        await _refresh_all_embeds(interaction.client)

# =================================================
# Embeds refresh
# =================================================

async def _refresh_match_message(bot, m):
    if not m.created_message_id:
        return
    ch = await bot.fetch_channel(m.channel_id)
    msg = await ch.fetch_message(m.created_message_id)
    t1, t2 = _find_team(m.team1_id), _find_team(m.team2_id)
    view = None if m.status == "DONE" else ForfeitView(m.id)
    await msg.edit(embed=embeds.embed_match(m, t1, t2), view=view)

async def _ensure_main_embeds(bot):
    ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
    if STATE.embeds.teams_msg_id is None:
        STATE.embeds.teams_msg_id = (await ch.send(embed=embeds.embed_teams(STATE.teams))).id
    if STATE.embeds.upcoming_msg_id is None:
        STATE.embeds.upcoming_msg_id = (await ch.send(embed=embeds.embed_upcoming(STATE.matches))).id
    if STATE.embeds.history_msg_id is None:
        STATE.embeds.history_msg_id = (await ch.send(embed=embeds.embed_history(STATE.matches))).id

async def _refresh_all_embeds(bot):
    await _ensure_main_embeds(bot)
    ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
    await (await ch.fetch_message(STATE.embeds.teams_msg_id)).edit(embed=embeds.embed_teams(STATE.teams))
    await (await ch.fetch_message(STATE.embeds.upcoming_msg_id)).edit(embed=embeds.embed_upcoming(STATE.matches))
    await (await ch.fetch_message(STATE.embeds.history_msg_id)).edit(embed=embeds.embed_history(STATE.matches))

# =================================================
# Reminder loop
# =================================================

async def _reminder_loop(bot):
    while True:
        try:
            now = datetime.now(PARIS_TZ)
            for m in STATE.matches:
                if m.status != "VALIDATED":
                    continue
                dt = _match_dt(m.date_str, m.time_str)
                if dt and timedelta(minutes=29) <= dt - now <= timedelta(minutes=30):
                    ch = await bot.fetch_channel(m.channel_id)
                    t1, t2 = _find_team(m.team1_id), _find_team(m.team2_id)
                    await ch.send(
                        f"{_mentions(t1, t2)}\n⏰ **Match dans 30 minutes**\n📸 Pensez au screen."
                    )
        except:
            pass
        await asyncio.sleep(60)

# =================================================
# Commands
# =================================================

def setup(tree: app_commands.CommandTree, bot: commands.Bot):

    @tree.command(name="reset")
    async def reset(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return
        STATE.reset()
        await interaction.followup.send("Tournoi réinitialisé.")

    # (les autres commandes /inscription /classe /tirage /tournoi sont inchangées
    # et doivent rester exactement comme dans ta version validée précédente)