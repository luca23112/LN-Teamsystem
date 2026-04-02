import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import LogType, TeamStatus
from bot.logging_service import log_action
from bot.permissions import is_team_or_admin
from bot.team_logic import apply_rank_role, auto_rank_position


class TeamCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.group = app_commands.Group(name="team", description="Team-Management")

        self.group.command(name="add", description="Teambeitritt")(self.add)
        self.group.command(name="kick", description="Teamkick")(self.kick)
        self.group.command(name="warn", description="Warn")(self.warn)
        self.group.command(name="resetwarns", description="Warns zurücksetzen")(self.resetwarns)
        self.group.command(name="up", description="Punkte erhöhen")(self.up)
        self.group.command(name="down", description="Punkte verringern")(self.down)
        self.group.command(name="setstatus", description="Status setzen")(self.setstatus)
        self.group.command(name="note", description="Notiz speichern")(self.note)
        self.group.command(name="notes", description="Notizen anzeigen")(self.notes)
        self.group.command(name="list", description="Teamliste")(self.list_team)
        self.group.command(name="ban", description="Teamban")(self.ban)
        self.group.command(name="unban", description="Teamunban")(self.unban)

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.group)

    async def _guard(self, interaction: discord.Interaction) -> dict | None:
        settings = self.bot.db.get_guild_settings(interaction.guild_id)
        if not isinstance(interaction.user, discord.Member):
            return None
        if not is_team_or_admin(interaction.user, settings):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return None
        return settings

    async def _auto_rank(self, member: discord.Member, user_data: dict, settings: dict, actor_id: int) -> dict:
        target = auto_rank_position(settings, user_data["points"])
        if target is None or target == user_data["rank_position"]:
            return user_data
        ranks = settings.get("rank_roles", [])
        old = ranks[user_data["rank_position"]] if user_data["rank_position"] >= 0 and user_data["rank_position"] < len(ranks) else None
        new = ranks[target] if target >= 0 else None
        await apply_rank_role(member, old["roleId"] if old else None, new["roleId"] if new else None)
        updated = self.bot.db.update_user(interaction_guild_id := member.guild.id, member.id, {"rank_position": target})
        self.bot.db.add_history(interaction_guild_id, member.id, "auto_rank", f"{old['name'] if old else 'Kein Rang'} -> {new['name'] if new else 'Kein Rang'}", actor_id)
        return updated

    async def add(self, interaction: discord.Interaction, user: discord.Member):
        settings = await self._guard(interaction)
        if not settings:
            return
        self.bot.db.update_user(interaction.guild_id, user.id, {
            "warns": 0,
            "points": 0,
            "rank_position": -1,
            "team_status": TeamStatus.ACTIVE.value,
            "banned": 0,
        })
        team_role_id = settings.get("team_role_id")
        if team_role_id:
            role = interaction.guild.get_role(int(team_role_id))
            if role:
                await user.add_roles(role)
        self.bot.db.add_history(interaction.guild_id, user.id, "team_add", None, interaction.user.id)
        await interaction.response.send_message(f"✅ {user.mention} wurde hinzugefügt.")

    async def kick(self, interaction: discord.Interaction, user: discord.Member, grund: str | None = None):
        settings = await self._guard(interaction)
        if not settings:
            return
        reason = grund or "Kein Grund"
        data = self.bot.db.get_user(interaction.guild_id, user.id)
        ranks = settings.get("rank_roles", [])
        old = ranks[data["rank_position"]] if data["rank_position"] >= 0 and data["rank_position"] < len(ranks) else None
        await apply_rank_role(user, old["roleId"] if old else None, None)
        self.bot.db.update_user(interaction.guild_id, user.id, {"team_status": TeamStatus.INACTIVE.value, "rank_position": -1})
        self.bot.db.add_history(interaction.guild_id, user.id, "team_kick", reason, interaction.user.id)
        await log_action(interaction.guild, settings, LogType.KICK, "Team Kick", f"{user} wurde gekickt ({reason})", 0xED4245)
        await interaction.response.send_message(f"✅ {user.mention} wurde gekickt.")

    async def warn(self, interaction: discord.Interaction, user: discord.Member, grund: str):
        settings = await self._guard(interaction)
        if not settings:
            return
        data = self.bot.db.get_user(interaction.guild_id, user.id)
        warns = data["warns"] + 1
        banned = 1 if warns >= int(settings.get("auto_ban_limit", 3)) else data["banned"]
        self.bot.db.update_user(interaction.guild_id, user.id, {"warns": warns, "banned": banned})
        self.bot.db.add_history(interaction.guild_id, user.id, "warn", grund, interaction.user.id)
        await log_action(interaction.guild, settings, LogType.WARN, "Warn", f"{user} wurde verwarnt: {grund}")
        await interaction.response.send_message(f"✅ {user.mention} hat nun {warns} Warn(s).")

    async def resetwarns(self, interaction: discord.Interaction, user: discord.Member):
        settings = await self._guard(interaction)
        if not settings:
            return
        self.bot.db.update_user(interaction.guild_id, user.id, {"warns": 0})
        self.bot.db.add_history(interaction.guild_id, user.id, "warn_reset", None, interaction.user.id)
        await interaction.response.send_message(f"✅ Warns von {user.mention} zurückgesetzt.")

    async def up(self, interaction: discord.Interaction, user: discord.Member, punkte: app_commands.Range[int, 1, 10000], grund: str | None = None):
        settings = await self._guard(interaction)
        if not settings:
            return
        data = self.bot.db.get_user(interaction.guild_id, user.id)
        updated = self.bot.db.update_user(interaction.guild_id, user.id, {"points": data["points"] + punkte})
        self.bot.db.add_history(interaction.guild_id, user.id, "points_up", grund, interaction.user.id)
        updated = await self._auto_rank(user, updated, settings, interaction.user.id)
        await interaction.response.send_message(f"✅ {user.mention} hat jetzt {updated['points']} Punkte.")

    async def down(self, interaction: discord.Interaction, user: discord.Member, punkte: app_commands.Range[int, 1, 10000], grund: str | None = None):
        settings = await self._guard(interaction)
        if not settings:
            return
        data = self.bot.db.get_user(interaction.guild_id, user.id)
        updated = self.bot.db.update_user(interaction.guild_id, user.id, {"points": data["points"] - punkte})
        self.bot.db.add_history(interaction.guild_id, user.id, "points_down", grund, interaction.user.id)
        updated = await self._auto_rank(user, updated, settings, interaction.user.id)
        await interaction.response.send_message(f"✅ {user.mention} hat jetzt {updated['points']} Punkte.")

    async def setstatus(self, interaction: discord.Interaction, user: discord.Member, status: str):
        settings = await self._guard(interaction)
        if not settings:
            return
        self.bot.db.update_user(interaction.guild_id, user.id, {"team_status": status})
        await interaction.response.send_message(f"✅ Status von {user.mention} auf **{status}** gesetzt.")

    @setstatus.autocomplete("status")
    async def status_autocomplete(self, _: discord.Interaction, current: str):
        choices = [TeamStatus.ACTIVE.value, TeamStatus.INACTIVE.value, TeamStatus.VACATION.value]
        return [app_commands.Choice(name=c, value=c) for c in choices if current.lower() in c.lower()]

    async def note(self, interaction: discord.Interaction, user: discord.Member, text: app_commands.Range[str, 1, 1000]):
        settings = await self._guard(interaction)
        if not settings:
            return
        self.bot.db.add_note(interaction.guild_id, user.id, text, interaction.user.id)
        await interaction.response.send_message(f"✅ Notiz für {user.mention} gespeichert.", ephemeral=True)

    async def notes(self, interaction: discord.Interaction, user: discord.Member):
        settings = await self._guard(interaction)
        if not settings:
            return
        notes = self.bot.db.get_notes(interaction.guild_id, user.id, 10)
        desc = "\n".join([f"• {n['note']} ({n['created_at']})" for n in notes]) if notes else "Keine Notizen."
        embed = discord.Embed(title=f"Notizen: {user}", description=desc, color=0x5865F2)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def list_team(self, interaction: discord.Interaction, status: str | None = None):
        settings = await self._guard(interaction)
        if not settings:
            return
        users = self.bot.db.list_team_users(interaction.guild_id, status if status and status != "alle" else None)[:20]
        desc = "\n".join([f"• <@{u['user_id']}> | Punkte {u['points']} | Warns {u['warns']} | {u['team_status']}" for u in users]) or "Keine Einträge"
        await interaction.response.send_message(embed=discord.Embed(title="Teamliste", description=desc, color=0x5865F2))

    async def ban(self, interaction: discord.Interaction, user: discord.Member, grund: str):
        settings = await self._guard(interaction)
        if not settings:
            return
        self.bot.db.update_user(interaction.guild_id, user.id, {"banned": 1})
        self.bot.db.add_history(interaction.guild_id, user.id, "ban", grund, interaction.user.id)
        await log_action(interaction.guild, settings, LogType.BAN, "Ban", f"{user} wurde gebannt: {grund}", 0xED4245)
        await interaction.response.send_message(f"✅ {user.mention} gebannt.")

    async def unban(self, interaction: discord.Interaction, user: discord.Member):
        settings = await self._guard(interaction)
        if not settings:
            return
        self.bot.db.update_user(interaction.guild_id, user.id, {"banned": 0})
        self.bot.db.add_history(interaction.guild_id, user.id, "unban", None, interaction.user.id)
        await interaction.response.send_message(f"✅ {user.mention} entbannt.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
