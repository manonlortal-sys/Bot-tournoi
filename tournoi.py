import asyncio
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands

import config
import permissions
import embeds
from state import STATE, Player, Team, Match

PARIS_TZ = ZoneInfo("Europe/Paris")


def _find_team(team_id: int) -> Team | None:
    for t in STATE.teams:
        if t.id == team_id:
            return t
    return None

def _alive_teams() -> list[Team]:
    return [t for t in STATE.teams if not t.eliminated]

def _channel_mentions_for_match(team1: Team, team2: Team) -> str:
    ids = [team1.players[0].user_id, team1.players[1].user_id, team2.players[0].user_id, team2.players[1].user_id]
    return " ".join(f"<@{i}>" for i in ids)

def _match_datetime(date_str: str, time_str: str) -> datetime | None:
    # date_str: JJ/MM or JJ/MM/AAAA ; time_str: HH:MM or 22h25
    ds = date_str.strip()
    ts = time_str.strip().lower().replace("h", ":")
    if len(ts.split(":")) == 2:
        hh, mm = ts.split(":")
    else:
        return None

    parts = ds.split("/")
    try:
        if len(parts) == 2:
            day, month = map(int, parts)
            year = datetime.now(PARIS_TZ).year
        else:
            day, month, year = map(int, parts)
        dt = datetime(year, month, day, int(hh), int(mm), tzinfo=PARIS_TZ)
        return dt
    except:
        return None


class MatchView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id

    @discord.ui.button(label="INDISPONIBLE", emoji=config.EMOJI_CROSS, style=discord.ButtonStyle.danger)
    async def indispo(self, interaction: discord.Interaction, button: discord.ui.Button):
        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        if not m:
            return await interaction.response.send_message("Match introuvable.", ephemeral=True)

        # ping player, as specified
        await interaction.response.send_message(
            f"{interaction.user.mention}\n\n{config.EMOJI_CROSS} **INDISPONIBLE**\n\n"
            "Tu n’es pas disponible à l’horaire prévu pour ce match.\n\n"
            "👉 Merci d’indiquer directement dans ce canal tes disponibilités alternatives "
            "afin que l’organisateur puisse modifier la date ou l’heure du combat.",
            ephemeral=False
        )
        m.status = "WAITING_AVAIL"
        await _refresh_all_embeds(interaction.client)

    @discord.ui.button(label="VALIDER", emoji=config.EMOJI_VALIDATE, style=discord.ButtonStyle.success)
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.can_manage_match(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        if not m:
            return await interaction.response.send_message("Match introuvable.", ephemeral=True)

        if m.status not in ("NEED_ORGA_VALIDATE", "WAITING_AVAIL", "VALIDATED"):
            # keep simple
            pass

        # Draw map if none
        if not m.map_name:
            picked = random.choice(config.MAPS)
            m.map_name = picked["name"]
            m.map_image = picked["image"]

        m.status = "VALIDATED"

        # Update embed match
        await _refresh_match_message(interaction.client, m)

        # Ping 4 players with final message
        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)
        if t1 and t2:
            mentions = _channel_mentions_for_match(t1, t2)
            await interaction.channel.send(
                f"{mentions}\n\n"
                f"{config.EMOJI_VALIDATE} **MATCH VALIDÉ**\n\n"
                f"⚔️ EQUIPE {m.team1_id} vs EQUIPE {m.team2_id}\n"
                f"📅 {m.date_str} à {m.time_str}\n"
                f"🗺️ Map : {m.map_name}\n\n"
                "Merci de poster le screen du résultat dans ce canal."
            )

        await _refresh_all_embeds(interaction.client)
        await interaction.response.send_message("Match validé.", ephemeral=True)

    @discord.ui.button(label="FORFAIT", emoji=config.EMOJI_FORFAIT, style=discord.ButtonStyle.secondary)
    async def forfait(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.can_manage_match(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        m = next((x for x in STATE.matches if x.id == self.match_id), None)
        if not m:
            return await interaction.response.send_message("Match introuvable.", ephemeral=True)

        # Forfeit => choose winner (orga will decide which team forfeits by clicking then selecting)
        # To stay simple: forfeit implies team2 forfeits if clicked in channel? Not acceptable.
        # So we ask ephemeral choice buttons.
        view = ForfeitChoiceView(self.match_id)
        await interaction.response.send_message("Quelle équipe déclare forfait ?", view=view, ephemeral=True)


class ForfeitChoiceView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=60)
        self.match_id = match_id

    @discord.ui.button(label="EQUIPE 1", style=discord.ButtonStyle.danger)
    async def team1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _apply_forfeit(interaction, self.match_id, forfeiting_team_index=1)

    @discord.ui.button(label="EQUIPE 2", style=discord.ButtonStyle.danger)
    async def team2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _apply_forfeit(interaction, self.match_id, forfeiting_team_index=2)


class ResultView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=3600)
        self.match_id = match_id

    @discord.ui.button(label="EQUIPE 1", style=discord.ButtonStyle.primary)
    async def win1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.can_manage_match(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)
        await _set_winner(interaction, self.match_id, winner_index=1)

    @discord.ui.button(label="EQUIPE 2", style=discord.ButtonStyle.primary)
    async def win2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not permissions.can_manage_match(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)
        await _set_winner(interaction, self.match_id, winner_index=2)


async def _set_winner(interaction: discord.Interaction, match_id: int, winner_index: int):
    m = next((x for x in STATE.matches if x.id == match_id), None)
    if not m:
        return await interaction.response.send_message("Match introuvable.", ephemeral=True)

    winner = m.team1_id if winner_index == 1 else m.team2_id
    loser = m.team2_id if winner_index == 1 else m.team1_id

    m.winner_team_id = winner
    m.status = "DONE"

    loser_team = _find_team(loser)
    if loser_team:
        loser_team.eliminated = True
        loser_team.eliminated_round = m.round_no

    await _refresh_match_message(interaction.client, m)
    await _refresh_all_embeds(interaction.client)

    await interaction.response.send_message(f"Victoire enregistrée : EQUIPE {winner}.", ephemeral=True)

async def _apply_forfeit(interaction: discord.Interaction, match_id: int, forfeiting_team_index: int):
    if not permissions.can_manage_match(interaction):
        return await interaction.response.send_message("Accès refusé.", ephemeral=True)

    m = next((x for x in STATE.matches if x.id == match_id), None)
    if not m:
        return await interaction.response.send_message("Match introuvable.", ephemeral=True)

    forfeiting = m.team1_id if forfeiting_team_index == 1 else m.team2_id
    winner = m.team2_id if forfeiting_team_index == 1 else m.team1_id

    m.winner_team_id = winner
    m.status = "DONE"

    forfeiting_team = _find_team(forfeiting)
    if forfeiting_team:
        forfeiting_team.eliminated = True
        forfeiting_team.eliminated_round = m.round_no

    await _refresh_match_message(interaction.client, m)
    await _refresh_all_embeds(interaction.client)

    await interaction.response.send_message(f"Forfait enregistré. Gagnant : EQUIPE {winner}.", ephemeral=True)


async def _ensure_main_embeds(bot: discord.Client):
    ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)

    # Teams embed
    if STATE.embeds.teams_msg_id is None:
        msg = await ch.send(embed=embeds.embed_teams(STATE.teams))
        STATE.embeds.teams_msg_id = msg.id

    # Upcoming embed
    if STATE.embeds.upcoming_msg_id is None:
        msg = await ch.send(embed=embeds.embed_upcoming(STATE.matches))
        STATE.embeds.upcoming_msg_id = msg.id

    # History embed
    if STATE.embeds.history_msg_id is None:
        msg = await ch.send(embed=embeds.embed_history(STATE.matches))
        STATE.embeds.history_msg_id = msg.id

async def _refresh_all_embeds(bot: discord.Client):
    await _ensure_main_embeds(bot)
    ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)

    # Teams
    try:
        msg = await ch.fetch_message(STATE.embeds.teams_msg_id)
        await msg.edit(embed=embeds.embed_teams(STATE.teams))
    except:
        STATE.embeds.teams_msg_id = None

    # Upcoming
    try:
        msg = await ch.fetch_message(STATE.embeds.upcoming_msg_id)
        await msg.edit(embed=embeds.embed_upcoming(STATE.matches))
    except:
        STATE.embeds.upcoming_msg_id = None

    # History
    try:
        msg = await ch.fetch_message(STATE.embeds.history_msg_id)
        await msg.edit(embed=embeds.embed_history(STATE.matches))
    except:
        STATE.embeds.history_msg_id = None

async def _refresh_match_message(bot: discord.Client, m: Match):
    ch = await bot.fetch_channel(m.channel_id)
    t1 = _find_team(m.team1_id)
    t2 = _find_team(m.team2_id)
    if not t1 or not t2:
        return

    if not m.created_message_id:
        return

    try:
        msg = await ch.fetch_message(m.created_message_id)
        await msg.edit(embed=embeds.embed_match(m, t1, t2), view=MatchView(m.id))
    except:
        pass

def setup(tree: app_commands.CommandTree, bot: commands.Bot):  # type: ignore
    # ---------- /inscription ----------
    @tree.command(name="inscription", description="Inscrire un joueur au tournoi")
    async def inscription(interaction: discord.Interaction, joueur: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        if any(p.user_id == joueur.id for p in STATE.players):
            return await interaction.followup.send("Déjà inscrit.")

        STATE.players.append(Player(user_id=joueur.id, cls=None))

        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        if STATE.embeds.players_msg_id is None:
            msg = await ch.send(embed=embeds.embed_players(STATE.players))
            STATE.embeds.players_msg_id = msg.id
        else:
            try:
                msg = await ch.fetch_message(STATE.embeds.players_msg_id)
                await msg.edit(embed=embeds.embed_players(STATE.players))
            except:
                msg = await ch.send(embed=embeds.embed_players(STATE.players))
                STATE.embeds.players_msg_id = msg.id

        await interaction.followup.send("Joueur inscrit.")

    # ---------- /classe ----------
    @tree.command(name="classe", description="Attribuer une classe à un joueur")
    async def classe(interaction: discord.Interaction, joueur: discord.Member, classe: str):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        classe = (classe or "").lower().strip()
        if classe not in config.CLASSES:
            return await interaction.followup.send("Classe invalide.")

        found = False
        for p in STATE.players:
            if p.user_id == joueur.id:
                p.cls = classe
                found = True
                break

        if not found:
            return await interaction.followup.send("Joueur non inscrit.")

        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        if STATE.embeds.players_msg_id:
            try:
                msg = await ch.fetch_message(STATE.embeds.players_msg_id)
                await msg.edit(embed=embeds.embed_players(STATE.players))
            except:
                pass

        await interaction.followup.send("Classe attribuée.")

    # ---------- /tirage (duos) ----------
    @tree.command(name="tirage", description="Tirage au sort des équipes (duos)")
    async def tirage(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        if not STATE.players or len(STATE.players) % 2 != 0:
            return await interaction.followup.send("Nombre de joueurs invalide (pair requis).")

        if any(p.cls is None for p in STATE.players):
            return await interaction.followup.send("Tous les joueurs doivent avoir une classe.")

        random.shuffle(STATE.players)

        STATE.teams.clear()
        tid = 1
        for i in range(0, len(STATE.players), 2):
            STATE.teams.append(Team(id=tid, players=(STATE.players[i], STATE.players[i+1])))
            tid += 1

        # delete players embed
        ch = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        if STATE.embeds.players_msg_id:
            try:
                msg = await ch.fetch_message(STATE.embeds.players_msg_id)
                await msg.delete()
            except:
                pass
            STATE.embeds.players_msg_id = None

        # create main embeds if missing
        await _ensure_main_embeds(bot)
        await _refresh_all_embeds(bot)

        await interaction.followup.send("Tirage effectué. Équipes créées.")

    # ---------- /tournoi (tirage des matchs round) ----------
    @tree.command(name="tournoi", description="Créer les matchs du round (date/heure)")
    async def tournoi_cmd(interaction: discord.Interaction, date: str, heure: str):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        alive = _alive_teams()
        if not alive or len(alive) % 2 != 0:
            return await interaction.followup.send("Nombre d'équipes invalide.")

        # start next round
        STATE.current_round += 1
        round_no = STATE.current_round

        # clear previous pending matches? No: keep history. But we only create if previous round done.
        prev_pending = [m for m in STATE.matches if m.round_no == round_no - 1 and m.status != "DONE"]
        if round_no > 1 and prev_pending:
            STATE.current_round -= 1
            return await interaction.followup.send("Le round précédent n’est pas terminé.")

        guild = interaction.guild
        category = guild.get_channel(config.MATCH_CATEGORY_ID)

        random.shuffle(alive)

        for i in range(0, len(alive), 2):
            t1 = alive[i]
            t2 = alive[i + 1]

            # channel perms: lead/admin + orga + the 4 players
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}

            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            orga_member = guild.get_member(config.ORGA_USER_ID)
            if orga_member:
                overwrites[orga_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            for pl in [t1.players[0], t1.players[1], t2.players[0], t2.players[1]]:
                mem = guild.get_member(pl.user_id)
                if mem:
                    overwrites[mem] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            name = config.MATCH_CHANNEL_TEMPLATE.format(a=t1.id, b=t2.id)
            match_channel = await guild.create_text_channel(name=name, category=category, overwrites=overwrites)

            mid = (max([m.id for m in STATE.matches], default=0) + 1)
            match = Match(
                id=mid,
                round_no=round_no,
                team1_id=t1.id,
                team2_id=t2.id,
                date_str=date,
                time_str=heure,
                channel_id=match_channel.id,
            )
            STATE.matches.append(match)

            # Ping players at start of message
            mentions = _channel_mentions_for_match(t1, t2)
            await match_channel.send(mentions)

            # Send embed match + view + add thumbs reaction
            embed_msg = await match_channel.send(
                embed=embeds.embed_match(match, t1, t2),
                view=MatchView(match.id)
            )
            match.created_message_id = embed_msg.id
            try:
                await embed_msg.add_reaction(config.EMOJI_THUMBS)
            except:
                pass

        await _refresh_all_embeds(bot)
        await interaction.followup.send(f"Round {round_no} créé : salons + matchs OK.")

    # ---------- /modifier (dans un canal de match) ----------
    @tree.command(name="modifier", description="Modifier date/heure du match (dans le salon du match)")
    async def modifier(interaction: discord.Interaction, date: str, heure: str):
        await interaction.response.defer(ephemeral=True)
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        # identify match by channel
        m = next((x for x in STATE.matches if x.channel_id == interaction.channel_id and x.status != "DONE"), None)
        if not m:
            return await interaction.followup.send("Aucun match actif dans ce salon.")

        m.date_str = date
        m.time_str = heure
        # map preserved by design
        m.thumbs.clear()
        m.status = "WAITING_AVAIL"

        await _refresh_match_message(bot, m)

        t1 = _find_team(m.team1_id)
        t2 = _find_team(m.team2_id)
        if t1 and t2:
            mentions = _channel_mentions_for_match(t1, t2)
            await interaction.channel.send(
                f"{mentions}\n\n📅 **Horaire modifié** : {date} à {heure}\n"
                "Merci de confirmer à nouveau votre disponibilité avec 👍."
            )

        await _refresh_all_embeds(bot)
        await interaction.followup.send("Match modifié.")

    # background reminder task
    bot.loop.create_task(_reminder_loop(bot))


async def _reminder_loop(bot: discord.Client):
    # check every 60 seconds
    while True:
        try:
            now = datetime.now(PARIS_TZ)
            for m in STATE.matches:
                if m.status != "VALIDATED":
                    continue
                if m.status == "DONE":
                    continue
                dt = _match_datetime(m.date_str, m.time_str)
                if not dt:
                    continue
                # window: [30m-45s, 30m+45s] to avoid spam
                delta = dt - now
                if timedelta(minutes=29, seconds=15) <= delta <= timedelta(minutes=30, seconds=45):
                    ch = await bot.fetch_channel(m.channel_id)
                    t1 = _find_team(m.team1_id)
                    t2 = _find_team(m.team2_id)
                    if not t1 or not t2:
                        continue
                    mentions = _channel_mentions_for_match(t1, t2)
                    map_txt = m.map_name or "En attente"
                    await ch.send(
                        f"{mentions}\n\n⏰ **Rappel** : match dans 30 minutes\n"
                        f"⚔️ EQUIPE {m.team1_id} vs EQUIPE {m.team2_id}\n"
                        f"📅 {m.date_str} à {m.time_str}\n"
                        f"🗺️ {map_txt}\n\n"
                        "Merci de poster le screen du résultat dans ce canal."
                    )
        except:
            pass
        await asyncio.sleep(60)