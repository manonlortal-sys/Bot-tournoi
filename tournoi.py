import random
import discord
from discord import app_commands

import storage
import permissions
import embeds
import config


def setup(tree, bot):

    @tree.command(name="tournoi", description="Lancer le tournoi et tirer les matchs")
    async def tournoi(
        interaction: discord.Interaction,
        date: str,
        heure: str
    ):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        data = storage.load_data()
        if data["phase"] != "teams":
            return await interaction.response.send_message(
                "Les équipes doivent être créées avant.", ephemeral=True
            )

        teams = data["teams"]
        if len(teams) % 2 != 0:
            return await interaction.response.send_message(
                "Nombre d'équipes invalide.", ephemeral=True
            )

        random.shuffle(teams)
        matches = []

        guild = interaction.guild
        category = guild.get_channel(config.MATCH_CATEGORY_ID)

        for i in range(0, len(teams), 2):
            t1 = teams[i]
            t2 = teams[i + 1]

            channel_name = f"equipe-{t1['id']}-vs-equipe-{t2['id']}"

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }

            for team in (t1, t2):
                for p in team["players"]:
                    member = guild.get_member(p["user_id"])
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=True,
                            read_message_history=True,
                        )

            orga = guild.get_member(config.ORGA_USER_ID)
            if orga:
                overwrites[orga] = discord.PermissionOverwrite(view_channel=True)

            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True)

            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
            )

            await channel.send(
                f"⚔️ **MATCH À JOUER**\n"
                f"EQUIPE {t1['id']} vs EQUIPE {t2['id']}\n\n"
                f"📅 {date}\n"
                f"🕒 {heure}"
            )

            matches.append(
                {
                    "team1": t1["id"],
                    "team2": t2["id"],
                    "date": date,
                    "time": heure,
                    "channel_id": channel.id,
                    "played": False,
                }
            )

        data["matches"] = matches
        data["phase"] = "matches"
        storage.save_data(data)

        channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
        msg = await channel.fetch_message(data["embeds"]["upcoming"])
        await msg.edit(embed=embeds.upcoming_embed(data))

        await interaction.response.send_message(
            "Matchs créés et salons ouverts.", ephemeral=True
        )