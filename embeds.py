import discord


def players_embed(data):
    embed = discord.Embed(
        title="👥 Tournoi 2v2 — Joueurs inscrits",
        description=(
            "Liste des joueurs inscrits au tournoi.\n"
            "Chaque joueur doit avoir une classe avant le tirage des équipes."
        ),
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
        title="🏆 Tournoi 2v2 — Équipes inscrites",
        description="Liste des équipes engagées dans le tournoi.\n❌ = équipe éliminée",
        color=discord.Color.gold(),
    )

    if not data["teams"]:
        embed.add_field(name="Aucune équipe", value="—", inline=False)
        return embed

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

    embed.add_field(name="Équipes", value="\n".join(alive + eliminated), inline=False)
    return embed


def upcoming_embed():
    return discord.Embed(
        title="📅 Tournoi 2v2 — Matchs à venir",
        color=discord.Color.gold(),
    )


def history_embed():
    return discord.Embed(
        title="📜 Tournoi 2v2 — Historique des matchs",
        color=discord.Color.gold(),
    )
