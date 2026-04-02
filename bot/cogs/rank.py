import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import LogType
from bot.logging_service import log_action
from bot.permissions import is_team_or_admin
from bot.team_logic import apply_rank_role


class RankCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _guard(self, interaction: discord.Interaction) -> dict | None:
        settings = self.bot.db.get_guild_settings(interaction.guild_id)
        if not isinstance(interaction.user, discord.Member):
            return None
        if not is_team_or_admin(interaction.user, settings):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return None
        return settings

    @app_commands.command(name="uprank", description="Rang erhöhen")
    async def uprank(self, interaction: discord.Interaction, user: discord.Member):
        settings = await self._guard(interaction)
        if not settings:
            return
        ranks = settings.get("rank_roles", [])
        if not ranks:
            await interaction.response.send_message("❌ Keine Ränge konfiguriert.", ephemeral=True)
            return
        data = self.bot.db.get_user(interaction.guild_id, user.id)
        old = data["rank_position"]
        new = min(old + 1, len(ranks) - 1)
        if new == old:
            await interaction.response.send_message("ℹ️ Bereits höchster Rang.", ephemeral=True)
            return
        old_rank = ranks[old] if old >= 0 else None
        new_rank = ranks[new]
        await apply_rank_role(user, old_rank["roleId"] if old_rank else None, new_rank["roleId"])
        self.bot.db.update_user(interaction.guild_id, user.id, {"rank_position": new})
        self.bot.db.add_history(interaction.guild_id, user.id, "rank_up", f"{old_rank['name'] if old_rank else 'Kein Rang'} -> {new_rank['name']}", interaction.user.id)
        await log_action(interaction.guild, settings, LogType.RANK, "Rank Up", f"{user} -> {new_rank['name']}", 0x57F287)
        await interaction.response.send_message(f"✅ {user.mention} auf **{new_rank['name']}** gesetzt.")

    @app_commands.command(name="downrank", description="Rang verringern")
    async def downrank(self, interaction: discord.Interaction, user: discord.Member):
        settings = await self._guard(interaction)
        if not settings:
            return
        ranks = settings.get("rank_roles", [])
        data = self.bot.db.get_user(interaction.guild_id, user.id)
        old = data["rank_position"]
        if old < 0:
            await interaction.response.send_message("ℹ️ Kein Rang vorhanden.", ephemeral=True)
            return
        new = old - 1
        old_rank = ranks[old] if old < len(ranks) else None
        new_rank = ranks[new] if new >= 0 and new < len(ranks) else None
        await apply_rank_role(user, old_rank["roleId"] if old_rank else None, new_rank["roleId"] if new_rank else None)
        self.bot.db.update_user(interaction.guild_id, user.id, {"rank_position": new})
        await log_action(interaction.guild, settings, LogType.RANK, "Rank Down", f"{user} -> {new_rank['name'] if new_rank else 'Kein Rang'}", 0xED4245)
        await interaction.response.send_message(f"✅ {user.mention} herabgestuft.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RankCog(bot))
