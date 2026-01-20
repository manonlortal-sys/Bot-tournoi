import random
import discord
import config
import embeds
from state import STATE
import permissions


class MatchView(discord.ui.View):
    def __init__(self, match):
        super().__init__(timeout=None)
        self.match = match

    @discord.ui.button(label="INDISPONIBLE", style=discord.ButtonStyle.danger, emoji="❌")
    async def unavailable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.match["players"]:
            return await interaction.response.send_message(
                "Tu n’es pas concerné par ce match.", ephemeral=True
            )

        await interaction.response.send_message(
            f"{interaction.user.mention} n’est pas disponible à cet horaire.\n"
            "👉 Merci d’indiquer vos disponibilités ici.",
            allowed_mentions=discord.AllowedMentions(users=True)
        )

    @discord.ui.button(label="VALIDER", style=discord.ButtonStyle.success, emoji="✅", disabled=True)
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != config.ORGA_USER_ID:
            return await interaction.response.send_message(
                "Seul l’organisateur peut valider le match.", ephemeral=True
            )

        await interaction.response.send_message("Match validé.", ephemeral=True)


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
        await channel.send(embed=embeds.teams_embed(STATE.teams))

        await interaction.followup.send("Équipes créées.")


    @tree.command(name="tournoi")
    async def tournoi(interaction: discord.Interaction, date: str, heure: str):
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

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }

            mentions = []
            players_ids = []

            # 🔹 JOUEURS DES DEUX ÉQUIPES
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
                        players_ids.append(member.id)

            # orga
            orga = guild.get_member(config.ORGA_USER_ID)
            if orga:
                overwrites[orga] = discord.PermissionOverwrite(view_channel=True)

            # admins
            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True)

            channel = await guild.create_text_channel(
                name=f"equipe-{t1['id']}-vs-equipe-{t2['id']}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title="⚔️ Match à jouer",
                color=discord.Color.gold()
            )

            embed.add_field(
                name=f"EQUIPE {t1['id']}",
                value=(
                    f"<@{t1['players'][0]['user_id']}> ({t1['players'][0]['class']})\n"
                    f"<@{t1['players'][1]['user_id']}> ({t1['players'][1]['class']})"
                ),
                inline=True
            )

            embed.add_field(
                name=f"EQUIPE {t2['id']}",
                value=(
                    f"<@{t2['players'][0]['user_id']}> ({t2['players'][0]['class']})\n"
                    f"<@{t2['players'][1]['user_id']}> ({t2['players'][1]['class']})"
                ),
                inline=True
            )

            embed.add_field(
                name="🗓️ Horaire",
                value=f"{date} à {heure}",
                inline=False
            )

            match = {
                "team1": t1["id"],
                "team2": t2["id"],
                "players": players_ids,
                "channel_id": channel.id
            }

            # 🔴 MESSAGE D’OUVERTURE : MENTION DES 4 JOUEURS
            msg = await channel.send(
                content=" ".join(mentions),
                embed=embed
            )

            # 👍 réaction
            await msg.add_reaction("👍")

            # boutons
            view = MatchView(match)
            await msg.edit(view=view)

            STATE.matches.append(match)

        embeds_channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        await embeds_channel.send(embed=embeds.upcoming_embed(STATE.matches))

        await interaction.followup.send("Matchs créés.")