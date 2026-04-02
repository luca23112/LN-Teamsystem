import discord


def is_admin(member: discord.Member, settings: dict) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    admin_role_id = settings.get("admin_role_id")
    return bool(admin_role_id and any(str(r.id) == str(admin_role_id) for r in member.roles))


def is_team_or_admin(member: discord.Member, settings: dict) -> bool:
    if is_admin(member, settings):
        return True
    team_role_id = settings.get("team_role_id")
    return bool(team_role_id and any(str(r.id) == str(team_role_id) for r in member.roles))
