import random
import discord
import config
import embeds
from state import STATE
import permissions


# ---------- VIEW POUR LES MATCHS ----------
class MatchView(discord.ui.View):
    def __init__(self, match, orga_id):
        super().__init__(timeout=None)
        self.match = match
        self.orga_id = orga_id
        self.ready = set()

    @discord.ui.button(label="PRÊT", style=discord.ButtonStyle.success, emoji="👍")
    async def ready_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id not in self.match["players"]:
            return await interaction.response.send_message(
                "Tu n’es pas concerné par ce match.", ephemeral=True
            )

        self.ready.add(user_id)
        await interaction.response.send_message("Noté 👍", ephemeral=True)

        # Si les 4 joueurs sont prêts
        if len(self.ready) == 4:
            channel = interaction.channel
            await channel.send(
                f"<@{self.orga_id}> — les 4 joueurs sont prêts. "
                f"Merci de **valider** le match."
            )
            self.enable_validate()

    @discord.ui.button(label="INDISPONIBLE", style=discord.ButtonStyle.danger, emoji="❌")
    async def unavailable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id not in self.match["players"]:
            return await interaction.response.send_message(
                "Tu n’es pas concerné par ce match.", ephemeral=True
            )

        await interaction.response.send_message(
            f"{interaction.user.mention} n’est pas disponible à cet horaire.\n"
            "👉 Merci d’indiquer vos disponibilités ici.",
            allowed_mentions=discord.AllowedMentions(users=True)
        )

    @discord.ui.button(label="VALIDER", style=discord.ButtonStyle.primary, emoji="✅", disabled=True)
    async def validate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.orga_id:
            return await interaction.response.send_message(
                "Seul l’organisateur peut valider.", ephemeral=True
            )

        await interaction.response.send_message(
            "Match validé. (prochaine étape : tirage de la map)", ephemeral=True
        )

    def enable_validate(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "VALIDER":
                child.disabled = False


# ---------- COMMANDES ----------
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

            # -------- PERMISSIONS --------
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }

            mentions = []
            players_ids = []

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

            orga = guild.get_member(config.ORGA_USER_ID)
            if orga:
                overwrites[orga] = discord.PermissionOverwrite(view_channel=True)

            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True)

            channel = await guild.create_text_channel(
                name=f"equipe-{t1['id']}-vs-equipe-{t2['id']}",
                category=category,
                overwrites=overwrites
            )

            # -------- EMBED MATCH --------
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
                "date": date,
                "time": heure,
                "channel_id": channel.id,
                "players": players_ids
            }

            view = MatchView(match, config.ORGA_USER_ID)

            await channel.send(
                content=" ".join(mentions),
                embed=embed,
                view=view
            )

            STATE.matches.append(match)

        embeds_channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        msg = await embeds_channel.send(
            embed=embeds.upcoming_embed(STATE.matches)
        )
        STATE.embeds["upcoming"] = msg.id

        await interaction.followup.send("Matchs créés.")