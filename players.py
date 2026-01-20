import discord

import embeds
import storage
import permissions
import config


def setup(tree, bot):

    @tree.command(name="inscription", description="Inscrire un joueur au tournoi")
    async def inscription(
        interaction: discord.Interaction,
        joueur: discord.Member
    ):
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        data = storage.load_data()
        if data["phase"] != "players":
            return await interaction.followup.send("Inscriptions fermées.")

        if any(p["user_id"] == joueur.id for p in data["players"]):
            return await interaction.followup.send("Ce joueur est déjà inscrit.")

        data["players"].append({"user_id": joueur.id, "class": None})
        storage.save_data(data)

        channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)

        if data["embeds"]["players"] is None:
            msg = await channel.send(embed=embeds.players_embed(data))
            data["embeds"]["players"] = msg.id
        else:
            msg = await channel.fetch_message(data["embeds"]["players"])
            await msg.edit(embed=embeds.players_embed(data))

        storage.save_data(data)
        await interaction.followup.send(f"{joueur.mention} inscrit.")

    @tree.command(name="classe", description="Attribuer une classe à un joueur")
    async def classe(
        interaction: discord.Interaction,
        joueur: discord.Member,
        classe: str
    ):
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        classe = classe.lower().strip()
        if classe not in config.CLASSES:
            return await interaction.followup.send("Classe invalide.")

        data = storage.load_data()
        if data["phase"] != "players":
            return await interaction.followup.send("Action impossible.")

        for p in data["players"]:
            if p["user_id"] == joueur.id:
                p["class"] = classe
                storage.save_data(data)

                channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
                msg = await channel.fetch_message(data["embeds"]["players"])
                await msg.edit(embed=embeds.players_embed(data))

                return await interaction.followup.send("Classe attribuée.")

        await interaction.followup.send("Joueur non inscrit.")