import discord


def auto_rank_position(settings: dict, points: int) -> int | None:
    if not settings.get("auto_rankups"):
        return None
    ranks = settings.get("rank_roles", [])
    if not ranks:
        return None
    threshold = max(10, int(settings.get("auto_rank_points", 100)))
    tier = points // threshold
    return max(-1, min(tier - 1, len(ranks) - 1))


async def apply_rank_role(member: discord.Member, old_role_id: str | None, new_role_id: str | None) -> None:
    if old_role_id:
        old = member.guild.get_role(int(old_role_id))
        if old and old in member.roles:
            await member.remove_roles(old, reason="Rank update")
    if new_role_id:
        new = member.guild.get_role(int(new_role_id))
        if new and new not in member.roles:
            await member.add_roles(new, reason="Rank update")
