import discord

def players_embed(players):
    e = discord.Embed(
        title="👥 Joueurs inscrits",
        color=discord.Color.blue()
    )
    e.description = (
        "\n".join(
            f"<@{p['user_id']}> — {p['class'] or 'classe non définie'}"
            for p in players
        )
        if players else "—"
    )
    return e


def teams_embed(teams):
    e = discord.Embed(
        title="🏆 Équipes",
        color=discord.Color.gold()
    )

    e.description = (
        "\n".join(
            f"EQUIPE {t['id']} — "
            f"<@{t['players'][0]['user_id']}> ({t['players'][0]['class']}) — "
            f"<@{t['players'][1]['user_id']}> ({t['players'][1]['class']})"
            for t in teams
        )
        if teams else "—"
    )
    return e


def upcoming_embed(matches):
    e = discord.Embed(
        title="📅 Matchs à venir",
        color=discord.Color.gold()
    )

    if not matches:
        e.description = "—"
        return e

    lines = []
    for m in matches:
        date = m.get("date", "?")
        time = m.get("time", "?")
        lines.append(
            f"EQUIPE {m['team1']} vs EQUIPE {m['team2']} — {date} {time}"
        )

    e.description = "\n".join(lines)
    return e