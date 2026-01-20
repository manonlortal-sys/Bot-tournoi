import random
import embeds
import storage
import permissions
import config


def setup(tree, bot):

    @tree.command(name="tirage")
    async def tirage(interaction):
        if not permissions.is_orga_or_admin(interaction):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)

        data = storage.load_data()
        if data["phase"] != "players":
            return await interaction.response.send_message("Tirage déjà fait.", ephemeral=True)

        if len(data["players"]) % 2 != 0 or not data["players"]:
            return await interaction.response.send_message("Nombre de joueurs invalide.", ephemeral=True)

        if any(p["class"] is None for p in data["players"]):
            return await interaction.response.send_message("Classe manquante.", ephemeral=True)

        random.shuffle(data["players"])
        teams = []
        for i in range(0, len(data["players"]), 2):
            teams.append({
                "id": len(teams) + 1,
                "players": [data["players"][i], data["players"][i + 1]],
                "eliminated": False,
            })

        data["teams"] = teams
        data["phase"] = "teams"
        storage.save_data(data)

        channel = await bot.fetch_channel(config.CHANNEL_EMBEDS_ID)

        if data["embeds"]["players"]:
            try:
                msg = await channel.fetch_message(data["embeds"]["players"])
                await msg.delete()
            except:
                pass
            data["embeds"]["players"] = None

        data["embeds"]["teams"] = (await channel.send(embed=embeds.teams_embed(data))).id
        data["embeds"]["upcoming"] = (await channel.send(embed=embeds.upcoming_embed())).id
        data["embeds"]["history"] = (await channel.send(embed=embeds.history_embed())).id

        storage.save_data(data)
        await interaction.response.send_message("Tirage effectué.", ephemeral=True)
