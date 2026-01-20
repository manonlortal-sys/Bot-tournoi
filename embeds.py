import discord

def players_embed(players):
    e = discord.Embed(title="👥 Joueurs inscrits", color=discord.Color.blue())
    e.description = "\n".join(
        f"<@{p['user_id']}> — {p['class'] or 'classe non définie'}"
        for p in players
    ) if players else "—"
    return e

def teams_embed(teams):
    e = discord.Embed(title="🏆 Équipes", color=discord.Color.gold())
    e.description = "\n".join(
        f"EQUIPE {t['id']} — <@{t['players'][0]['user_id']}> ({t['players'][0]['class']}) — "
        f"<@{t['players'][1]['user_id']}> ({t['players'][1]['class']})"
        for t in teams
    ) if teams else "—"
    return e

def upcoming_embed(matches):
    e = discord.Embed(title="📅 Matchs à venir", color=discord.Color.gold())
    e.description = "\n".join(
        f"EQUIPE {m['team1']} vs EQUIPE {m['team2']} — {m['date']} {m['time']}"
        for m in matches
    ) if matches else "—"
    return e