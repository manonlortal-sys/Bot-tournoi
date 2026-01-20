import os
import discord
from discord.ext import commands

import tournoi

intents = discord.Intents.default()
intents.message_content = True  # requis pour détecter les screens (attachments)

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot prêt : {bot.user}")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Track thumbs for availability on the embed message in a match channel
    if payload.user_id == bot.user.id:
        return
    if str(payload.emoji) != "👍":
        return

    # Find match by created_message_id
    from state import STATE
    import permissions
    import config as cfg
    import embeds
    import tournoi as tour_mod

    m = next((x for x in STATE.matches if x.created_message_id == payload.message_id and x.status != "DONE"), None)
    if not m:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    # Only players of the match can count
    t1 = tour_mod._find_team(m.team1_id)
    t2 = tour_mod._find_team(m.team2_id)
    if not t1 or not t2:
        return

    allowed = {t1.players[0].user_id, t1.players[1].user_id, t2.players[0].user_id, t2.players[1].user_id}
    if payload.user_id not in allowed:
        return

    m.thumbs.add(payload.user_id)

    # If all 4 thumbs => ping orga and switch status
    if len(m.thumbs) == 4 and m.status != "NEED_ORGA_VALIDATE":
        m.status = "NEED_ORGA_VALIDATE"
        ch = await bot.fetch_channel(m.channel_id)
        await ch.send(f"Tous les joueurs sont disponibles.\n<@{cfg.ORGA_USER_ID}> merci de confirmer le match via ✅ VALIDER.")
        await tour_mod._refresh_match_message(bot, m)
        await tour_mod._refresh_all_embeds(bot)

@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    # If an image is posted in a match channel => ask orga who won
    from state import STATE
    import permissions as perms
    import tournoi as tour_mod
    import config as cfg

    m = next((x for x in STATE.matches if x.channel_id == message.channel.id and x.status == "VALIDATED"), None)
    if not m:
        return

    has_image = any(att.content_type and att.content_type.startswith("image/") for att in message.attachments)
    if not has_image:
        return

    # Ask winner
    t1 = tour_mod._find_team(m.team1_id)
    t2 = tour_mod._find_team(m.team2_id)
    if not t1 or not t2:
        return

    view = tour_mod.ResultView(m.id)
    await message.channel.send(
        f"{cfg.EMOJI_TROPHY} **Résultat détecté**\n"
        f"Match EQUIPE {m.team1_id} contre EQUIPE {m.team2_id} — qui a gagné ?\n"
        f"(Seul l’organisateur/admin peut cliquer)",
        view=view
    )

tournoi.setup(bot.tree, bot)

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN manquant")
bot.run(token)