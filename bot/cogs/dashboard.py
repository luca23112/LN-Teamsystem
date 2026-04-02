import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import is_team_or_admin


class DashboardView(discord.ui.View):
    def __init__(self, cog: "DashboardCog", user_id: int, page: int = 0) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id
        self.page = page

    async def _update(self, interaction: discord.Interaction, new_page: int) -> None:
        self.page = max(0, new_page)
        embed = self.cog.build_embed(interaction.guild_id, self.user_id, self.page)
        await interaction.response.edit_message(embed=embed, view=DashboardView(self.cog, self.user_id, self.page))

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._update(interaction, self.page - 1)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._update(interaction, self.page + 1)


class DashboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def build_embed(self, guild_id: int, user_id: int, page: int) -> discord.Embed:
        settings = self.bot.db.get_guild_settings(guild_id)
        data = self.bot.db.get_user(guild_id, user_id)
        history = self.bot.db.get_history(guild_id, user_id, 5, page * 5)
        rank = "Kein Rang"
        if data["rank_position"] >= 0 and data["rank_position"] < len(settings.get("rank_roles", [])):
            rank = settings["rank_roles"][data["rank_position"]]["name"]

        lines = "\n".join([f"• {h['action']} – {h['reason'] or '-'} ({h['created_at']})" for h in history]) or "Keine Historie"
        embed = discord.Embed(title=f"Team-Dashboard: {user_id}", color=0x5865F2)
        embed.add_field(name="Warns", value=str(data["warns"]))
        embed.add_field(name="Punkte", value=str(data["points"]))
        embed.add_field(name="Rang", value=rank)
        embed.add_field(name="Status", value=data["team_status"])
        embed.add_field(name="Bann", value="Ja" if data["banned"] else "Nein")
        embed.add_field(name=f"Historie (Seite {page+1})", value=lines, inline=False)
        return embed

    @app_commands.command(name="team-dashboard", description="Team Dashboard anzeigen")
    async def team_dashboard(self, interaction: discord.Interaction, user: discord.Member):
        settings = self.bot.db.get_guild_settings(interaction.guild_id)
        if not isinstance(interaction.user, discord.Member) or not is_team_or_admin(interaction.user, settings):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return
        embed = self.build_embed(interaction.guild_id, user.id, 0)
        await interaction.response.send_message(embed=embed, view=DashboardView(self, user.id, 0))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DashboardCog(bot))
