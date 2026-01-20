import discord
import config
import embeds
from state import STATE
import permissions

def setup(tree, bot):

    @tree.command(name="inscription")
    async def inscription(interaction: discord.Interaction, joueur: discord.Member):
        await interaction.response.defer(ephemeral=True)

        if not permissions.is_orga_or_admin(interaction):
            return await interaction.followup.send("Accès refusé.")

        if any(p["user_id"] == joueur.id for p in STATE.players):
            return await interaction.followup.send("Déjà inscrit.")

        STATE.players.append({"user_id": joueur.id, "class": None})

        channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)

        if STATE.embeds["players"] is None:
            msg = await channel.send(embed=embeds.players_embed(STATE.players))
            STATE.embeds["players"] = msg.id
        else:
            msg = await channel.fetch_message(STATE.embeds["players"])
            await msg.edit(embed=embeds.players_embed(STATE.players))

        await interaction.followup.send("Joueur inscrit.")

    @tree.command(name="classe")
    async def classe(interaction: discord.Interaction, joueur: discord.Member, classe: str):
        await interaction.response.defer(ephemeral=True)

        for p in STATE.players:
            if p["user_id"] == joueur.id:
                p["class"] = classe
                channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)
                msg = await channel.fetch_message(STATE.embeds["players"])
                await msg.edit(embed=embeds.players_embed(STATE.players))
                return await interaction.followup.send("Classe attribuée.")

        await interaction.followup.send("Joueur non inscrit.")