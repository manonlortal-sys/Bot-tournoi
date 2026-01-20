import random
import discord

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
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        data = storage.load_data()

        if data["phase"] != "teams":
            return await interaction.followup.send(
                "Les équipes doivent être créées avant."
            )

        teams = data["teams"]
        if not teams or len(teams) % 2 != 0:
            return await interaction.followup.send(
                "Nombre d'équipes invalide."
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

        # ---- EMBED UPCOMING : CREATE OR UPDATE ----
        embeds_channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)

        upcoming_id = data["embeds"].get("upcoming")

        if upcoming_id is None:
            msg = await embeds_channel.send(
                embed=embeds.upcoming_embed(data)
            )
            data["embeds"]["upcoming"] = msg.id
            storage.save_data(data)
        else:
            try:
                msg = await embeds_channel.fetch_message(upcoming_id)
                await msg.edit(embed=embeds.upcoming_embed(data))
            except discord.NotFound:
                msg = await embeds_channel.send(
                    embed=embeds.upcoming_embed(data)
                )
                data["embeds"]["upcoming"] = msg.id
                storage.save_data(data)

        await interaction.followup.send("Matchs créés et salons ouverts.")