import discord


def players_embed(data):
    embed = discord.Embed(
        title="👥 Tournoi 2v2 — Joueurs inscrits",
        description="Chaque joueur doit avoir une classe avant le tirage.",
        color=discord.Color.blue(),
    )

    if not data["players"]:
        embed.add_field(name="Aucun joueur", value="—", inline=False)
        return embed

    lines = []
    for p in data["players"]:
        cls = p["class"] if p["class"] else "classe non définie"
        lines.append(f"<@{p['user_id']}> — {cls}")

    embed.add_field(name="Joueurs", value="\n".join(lines), inline=False)
    return embed


def teams_embed(data):
    embed = discord.Embed(
        title="🏆 Tournoi 2v2 — Équipes",
        description="Classement en cours",
        color=discord.Color.gold(),
    )

    alive, eliminated = [], []

    for t in data["teams"]:
        p1, p2 = t["players"]
        line = (
            f"EQUIPE {t['id']} — "
            f"<@{p1['user_id']}> ({p1['class']}) — "
            f"<@{p2['user_id']}> ({p2['class']})"
        )
        (eliminated if t.get("eliminated") else alive).append(
            f"❌ {line}" if t.get("eliminated") else line
        )

    embed.add_field(
        name="Équipes",
        value="\n".join(alive + eliminated) if alive or eliminated else "—",
        inline=False,
    )
    return embed


def upcoming_embed(data):
    embed = discord.Embed(
        title="📅 Tournoi 2v2 — Matchs à venir",
        color=discord.Color.gold(),
    )

    if not data["matches"]:
        embed.add_field(name="Aucun match", value="—", inline=False)
        return embed

    lines = []
    for m in data["matches"]:
        lines.append(
            f"EQUIPE {m['team1']} vs EQUIPE {m['team2']} — {m['date']} {m['time']}"
        )

    embed.add_field(name="Matchs", value="\n".join(lines), inline=False)
    return embed


def history_embed():
    return discord.Embed(
        title="📜 Tournoi 2v2 — Historique",
        color=discord.Color.gold(),
    )