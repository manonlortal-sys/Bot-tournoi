import config

def is_orga(interaction) -> bool:
    return interaction.user.id == config.ORGA_USER_ID

def is_admin_role(member) -> bool:
    return any(r.id == config.ADMIN_ROLE_ID for r in getattr(member, "roles", []))

def is_orga_or_admin(interaction) -> bool:
    return is_orga(interaction) or is_admin_role(interaction.user)

def can_manage_match(interaction) -> bool:
    return is_orga_or_admin(interaction)

def is_orga_or_admin_user(guild, user_id: int) -> bool:
    if user_id == config.ORGA_USER_ID:
        return True
    m = guild.get_member(user_id)
    if not m:
        return False
    return is_admin_role(m)