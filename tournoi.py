import random
import discord
import config
import embeds
from state import STATE
import permissions

def setup(tree, bot):

    @tree.command(name="tirage")
    async def tirage(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if len(STATE.players) % 2 != 0 or not STATE.players:
            return await interaction.followup.send("Nombre de joueurs invalide.")

        if any(p["class"] is None for p in STATE.players):
            return await interaction.followup.send("Classes manquantes.")

        random.shuffle(STATE.players)
        STATE.teams = []

        for i in range(0, len(STATE.players), 2):
            STATE.teams.append({
                "id": len(STATE.teams) + 1,
                "players": [STATE.players[i], STATE.players[i + 1]]
            })

        channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        msg = await channel.send(embed=embeds.teams_embed(STATE.teams))
        STATE.embeds["teams"] = msg.id

        await interaction.followup.send("Équipes tirées.")


    @tree.command(name="tournoi")
    async def tournoi(interaction: discord.Interaction, date: str, heure: str):
        await interaction.response.defer(ephemeral=True)

        if len(STATE.teams) % 2 != 0 or not STATE.teams:
            return await interaction.followup.send("Nombre d'équipes invalide.")

        guild = interaction.guild
        category = guild.get_channel(config.MATCH_CATEGORY_ID)

        random.shuffle(STATE.teams)
        STATE.matches = []

        for i in range(0, len(STATE.teams), 2):
            t1, t2 = STATE.teams[i], STATE.teams[i + 1]

            channel = await guild.create_text_channel(
                name=f"equipe-{t1['id']}-vs-equipe-{t2['id']}",
                category=category
            )

            await channel.send(
                f"⚔️ EQUIPE {t1['id']} vs EQUIPE {t2['id']}\n📅 {date} 🕒 {heure}"
            )

            STATE.matches.append({
                "team1": t1["id"],
                "team2": t2["id"],
                "date": date,
                "time": heure,
                "channel_id": channel.id
            })

        embeds_channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        await embeds_channel.send(
            embed=embeds.upcoming_embed(STATE.matches)
        )

        await interaction.followup.send("Matchs créés.")