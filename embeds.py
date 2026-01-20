import discord
import config
from state import Player, Team, Match

GOLD = discord.Color.gold()

def embed_players(players: list[Player]) -> discord.Embed:
    e = discord.Embed(
        title="👥 Tournoi 2v2 — Joueurs inscrits",
        description="Chaque joueur doit avoir une classe avant le tirage des équipes.",
        color=discord.Color.blue()
    )
    if not players:
        e.add_field(name="Aucun joueur", value="—", inline=False)
        return e

    lines = []
    for p in players:
        cls = p.cls if p.cls else "classe non définie"
        lines.append(f"<@{p.user_id}> — {cls}")
    e.add_field(name="Joueurs", value="\n".join(lines), inline=False)
    return e

def embed_teams(teams: list[Team]) -> discord.Embed:
    e = discord.Embed(
        title="🏆 Tournoi 2v2 — Classement",
        description="Les équipes éliminées sont affichées en bas. ❌ = éliminée",
        color=GOLD
    )

    if not teams:
        e.add_field(name="Équipes", value="—", inline=False)
        return e

    alive_lines = []
    elim_lines = []

    for t in sorted(teams, key=lambda x: x.id):
        p1, p2 = t.players
        line = (
            f"EQUIPE {t.id} — "
            f"<@{p1.user_id}> ({p1.cls}) — "
            f"<@{p2.user_id}> ({p2.cls})"
        )
        if t.eliminated:
            elim_lines.append(f"{config.EMOJI_CROSS} {line}")
        else:
            alive_lines.append(line)

    e.add_field(name="Équipes", value="\n".join(alive_lines + elim_lines), inline=False)
    return e

def embed_upcoming(matches: list[Match]) -> discord.Embed:
    e = discord.Embed(
        title="📅 Tournoi 2v2 — Matchs à venir",
        color=GOLD
    )
    if not matches:
        e.add_field(name="Matchs", value="—", inline=False)
        return e

    # Only not done
    pending = [m for m in matches if m.status != "DONE"]
    if not pending:
        e.add_field(name="Matchs", value="—", inline=False)
        return e

    lines = []
    for m in pending:
        status = {
            "WAITING_AVAIL": "🟡 dispo",
            "NEED_ORGA_VALIDATE": "🟢 dispo OK — orga",
            "VALIDATED": "✅ validé",
            "DONE": "🏁 terminé"
        }.get(m.status, m.status)

        map_part = f" — 🗺️ {m.map_name}" if m.map_name else ""
        lines.append(
            f"(R{m.round_no}) EQUIPE {m.team1_id} vs EQUIPE {m.team2_id} — {m.date_str} {m.time_str}{map_part} — {status}"
        )

    e.add_field(name="Matchs", value="\n".join(lines), inline=False)
    return e

def embed_history(matches: list[Match]) -> discord.Embed:
    e = discord.Embed(
        title="📜 Tournoi 2v2 — Historique",
        color=GOLD
    )
    done = [m for m in matches if m.status == "DONE" and m.winner_team_id]
    if not done:
        e.add_field(name="Résultats", value="—", inline=False)
        return e

    lines = []
    for m in done:
        loser = m.team2_id if m.winner_team_id == m.team1_id else m.team1_id
        lines.append(
            f"(R{m.round_no}) {config.EMOJI_TROPHY} EQUIPE {m.winner_team_id} a gagné vs EQUIPE {loser}"
        )

    e.add_field(name="Résultats", value="\n".join(lines), inline=False)
    return e

def embed_match(match: Match, team1: Team, team2: Team) -> discord.Embed:
    e = discord.Embed(
        title="⚔️ MATCH — TOURNOI 2v2",
        description=f"EQUIPE {match.team1_id} vs EQUIPE {match.team2_id}",
        color=GOLD
    )

    p1a, p1b = team1.players
    p2a, p2b = team2.players

    teams_block = (
        f"**EQUIPE {team1.id}**\n"
        f"• <@{p1a.user_id}> — {p1a.cls}\n"
        f"• <@{p1b.user_id}> — {p1b.cls}\n\n"
        f"**EQUIPE {team2.id}**\n"
        f"• <@{p2a.user_id}> — {p2a.cls}\n"
        f"• <@{p2b.user_id}> — {p2b.cls}"
    )
    e.add_field(name="👥 Équipes", value=teams_block, inline=False)
    e.add_field(name="📅 Date & Heure", value=f"{match.date_str} à {match.time_str}", inline=False)

    if match.map_name:
        e.add_field(name="🗺️ Map", value=match.map_name, inline=False)
        if match.map_image:
            e.set_image(url=match.map_image)
    else:
        e.add_field(name="🗺️ Map", value="En attente de tirage", inline=False)

    status_txt = {
        "WAITING_AVAIL": "🟡 En attente des disponibilités",
        "NEED_ORGA_VALIDATE": "🟢 Tous disponibles — validation requise",
        "VALIDATED": "✅ Match validé",
        "DONE": "🏁 Match terminé",
    }.get(match.status, match.status)

    e.add_field(name="📌 Statut", value=status_txt, inline=False)
    e.set_footer(text="Merci d’indiquer votre disponibilité")
    return e