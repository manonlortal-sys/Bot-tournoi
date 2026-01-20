import discord
from discord import app_commands

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
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        data = storage.load_data()
        if data["phase"] != "players":
            return await interaction.response.send_message("Inscriptions fermées.", ephemeral=True)

        if any(p["user_id"] == joueur.id for p in data["players"]):
            return await interaction.response.send_message("Déjà inscrit.", ephemeral=True)

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
        await interaction.response.send_message("Joueur inscrit.", ephemeral=True)

    @tree.command(name="classe", description="Attribuer une classe à un joueur")
    async def classe(
        interaction: discord.Interaction,
        joueur: discord.Member,
        classe: str
    ):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        classe = classe.lower().strip()
        if classe not in config.CLASSES:
            return await interaction.response.send_message("Classe invalide.", ephemeral=True)

        data = storage.load_data()
        if data["phase"] != "players":
            return await interaction.response.send_message("Action impossible.", ephemeral=True)

        for p in data["players"]:
            if p["user_id"] == joueur.id:
                p["class"] = classe
                storage.save_data(data)

                channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
                msg = await channel.fetch_message(data["embeds"]["players"])
                await msg.edit(embed=embeds.players_embed(data))

                return await interaction.response.send_message("Classe attribuée.", ephemeral=True)

        await interaction.response.send_message("Joueur non inscrit.", ephemeral=True)
