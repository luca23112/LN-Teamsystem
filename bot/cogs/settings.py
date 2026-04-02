import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import is_admin


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings_group = app_commands.Group(name="settings", description="Bot Einstellungen")
        self.team_group = app_commands.Group(name="team", description="Team Settings", parent=self.settings_group)

        self.team_group.command(name="set-logchannel", description="Setzt Logchannel")(self.set_logchannel)
        self.team_group.command(name="set-dashboard", description="Setzt Dashboardchannel")(self.set_dashboard)
        self.team_group.command(name="set-role", description="Setzt Team/Admin Rolle")(self.set_role)
        self.team_group.command(name="set-autoban", description="Setzt Warnlimit")(self.set_autoban)
        self.team_group.command(name="set-auto-rank-points", description="Setzt Punkte pro Rank-Stufe")(self.set_auto_rank_points)
        self.team_group.command(name="rank-add", description="Fügt Rang ein")(self.rank_add)
        self.team_group.command(name="rank-remove", description="Entfernt Rang")(self.rank_remove)
        self.team_group.command(name="rank-toggle-auto", description="Aktiviert Auto-Rank")(self.rank_toggle_auto)
        self.team_group.command(name="show", description="Zeigt Settings")(self.show)

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.settings_group)

    async def _admin_guard(self, interaction: discord.Interaction) -> dict | None:
        settings = self.bot.db.get_guild_settings(interaction.guild_id)
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user, settings):
            await interaction.response.send_message("❌ Nur Admins.", ephemeral=True)
            return None
        return settings

    async def set_logchannel(self, interaction: discord.Interaction, typ: str, channel: discord.TextChannel):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        if typ not in {"general", "warn", "ban", "kick", "rank", "points"}:
            await interaction.response.send_message("❌ Ungültiger Typ.", ephemeral=True)
            return
        self.bot.db.update_guild_settings(interaction.guild_id, {f"log_{typ}_channel_id": str(channel.id)})
        await interaction.response.send_message(f"✅ Logchannel für {typ}: {channel.mention}")

    async def set_dashboard(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        self.bot.db.update_guild_settings(interaction.guild_id, {"dashboard_channel_id": str(channel.id)})
        await interaction.response.send_message(f"✅ Dashboardchannel: {channel.mention}")

    async def set_role(self, interaction: discord.Interaction, typ: str, rolle: discord.Role):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        if typ not in {"team", "admin"}:
            await interaction.response.send_message("❌ typ muss team/admin sein.", ephemeral=True)
            return
        key = "team_role_id" if typ == "team" else "admin_role_id"
        self.bot.db.update_guild_settings(interaction.guild_id, {key: str(rolle.id)})
        await interaction.response.send_message(f"✅ {typ}-Rolle gesetzt: {rolle.mention}")

    async def set_autoban(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 20]):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        self.bot.db.update_guild_settings(interaction.guild_id, {"auto_ban_limit": limit})
        await interaction.response.send_message(f"✅ Auto-Ban-Limit: {limit}")

    async def set_auto_rank_points(self, interaction: discord.Interaction, punkte: app_commands.Range[int, 10, 10000]):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        self.bot.db.update_guild_settings(interaction.guild_id, {"auto_rank_points": punkte})
        await interaction.response.send_message(f"✅ Auto-Rank-Schwelle: {punkte} Punkte")

    async def rank_add(self, interaction: discord.Interaction, position: app_commands.Range[int, 0, 50], rolle: discord.Role, name: str | None = None):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        ranks = settings.get("rank_roles", [])
        ranks.insert(position, {"roleId": str(rolle.id), "name": name or rolle.name})
        self.bot.db.update_guild_settings(interaction.guild_id, {"rank_roles": ranks})
        await interaction.response.send_message(f"✅ Rang hinzugefügt: {name or rolle.name}")

    async def rank_remove(self, interaction: discord.Interaction, position: app_commands.Range[int, 0, 50]):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        ranks = settings.get("rank_roles", [])
        if position >= len(ranks):
            await interaction.response.send_message("❌ Position nicht vorhanden.", ephemeral=True)
            return
        removed = ranks.pop(position)
        self.bot.db.update_guild_settings(interaction.guild_id, {"rank_roles": ranks})
        await interaction.response.send_message(f"✅ Rang entfernt: {removed['name']}")

    async def rank_toggle_auto(self, interaction: discord.Interaction, aktiv: bool):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        self.bot.db.update_guild_settings(interaction.guild_id, {"auto_rankups": aktiv})
        await interaction.response.send_message(f"✅ Auto-Rankups: {'aktiv' if aktiv else 'inaktiv'}")

    async def show(self, interaction: discord.Interaction):
        settings = await self._admin_guard(interaction)
        if not settings:
            return
        rank_text = "\n".join([f"{i}. {r['name']} (<@&{r['roleId']}>)" for i, r in enumerate(settings.get("rank_roles", []))]) or "Keine"
        embed = discord.Embed(title="Team Settings", color=0x5865F2)
        embed.add_field(name="Team Rolle", value=f"<@&{settings['team_role_id']}>" if settings.get("team_role_id") else "Nicht gesetzt")
        embed.add_field(name="Admin Rolle", value=f"<@&{settings['admin_role_id']}>" if settings.get("admin_role_id") else "Nicht gesetzt")
        embed.add_field(name="Auto-Ban", value=str(settings.get("auto_ban_limit", 3)))
        embed.add_field(name="Auto-Rankups", value="Aktiv" if settings.get("auto_rankups") else "Inaktiv")
        embed.add_field(name="Auto-Rank Punkte", value=str(settings.get("auto_rank_points", 100)))
        embed.add_field(name="Ränge", value=rank_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
