import config


def is_orga_or_admin(interaction):
    if interaction.user.id == config.ORGA_USER_ID:
        return True
    if not hasattr(interaction.user, "roles"):
        return False
    return any(r.id == config.ADMIN_ROLE_ID for r in interaction.user.roles)
