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

        await interaction.followup.send("Équipes créées.")


    @tree.command(name="tournoi")
    async def tournoi(
        interaction: discord.Interaction,
        date: str,
        heure: str
    ):
        await interaction.response.defer(ephemeral=True)

        if len(STATE.teams) % 2 != 0 or not STATE.teams:
            return await interaction.followup.send("Nombre d'équipes invalide.")

        guild = interaction.guild
        category = guild.get_channel(config.MATCH_CATEGORY_ID)

        STATE.matches = []

        random.shuffle(STATE.teams)

        for i in range(0, len(STATE.teams), 2):
            t1 = STATE.teams[i]
            t2 = STATE.teams[i + 1]

            # ---- PERMISSIONS ----
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }

            # joueurs des deux équipes
            mentions = []

            for team in (t1, t2):
                for p in team["players"]:
                    member = guild.get_member(p["user_id"])
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=True,
                            read_message_history=True,
                        )
                        mentions.append(member.mention)

            # organisateur
            orga = guild.get_member(config.ORGA_USER_ID)
            if orga:
                overwrites[orga] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

            # rôle admin
            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

            # ---- CRÉATION DU SALON ----
            channel = await guild.create_text_channel(
                name=f"equipe-{t1['id']}-vs-equipe-{t2['id']}",
                category=category,
                overwrites=overwrites
            )

            # ---- MESSAGE D’OUVERTURE AVEC MENTIONS ----
            await channel.send(
                f"{' '.join(mentions)}\n\n"
                f"⚔️ **MATCH À JOUER**\n"
                f"EQUIPE {t1['id']} vs EQUIPE {t2['id']}\n\n"
                f"📅 {date}\n"
                f"🕒 {heure}"
            )

            STATE.matches.append({
                "team1": t1["id"],
                "team2": t2["id"],
                "date": date,
                "time": heure,
                "channel_id": channel.id
            })

        # ---- EMBED MATCHS À VENIR ----
        embeds_channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        msg = await embeds_channel.send(
            embed=embeds.upcoming_embed(STATE.matches)
        )
        STATE.embeds["upcoming"] = msg.id

        await interaction.followup.send("Matchs créés.")