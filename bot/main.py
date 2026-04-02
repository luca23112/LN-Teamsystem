import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot.database import DataStore


class TeamSystemBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = DataStore(os.getenv("DB_PATH", "./data/teamsystem.sqlite3"))

    async def setup_hook(self) -> None:
        cogs = [
            "bot.cogs.team",
            "bot.cogs.rank",
            "bot.cogs.dashboard",
            "bot.cogs.settings",
        ]
        for cog in cogs:
            await self.load_extension(cog)

        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        print(f"[READY] {self.user} ({self.user.id})")


async def main() -> None:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN fehlt in der .env")

    bot = TeamSystemBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
