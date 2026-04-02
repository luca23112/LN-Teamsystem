import discord

from bot.constants import LogType


async def log_action(guild: discord.Guild, settings: dict, log_type: LogType, title: str, description: str, color: int = 0x5865F2) -> None:
    channel_id = settings.get(f"log_{log_type.value}_channel_id") or settings.get("log_general_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        return

    embed = discord.Embed(title=title, description=description, color=color)
    await channel.send(embed=embed)
