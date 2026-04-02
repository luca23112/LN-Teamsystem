import json
import sqlite3
from pathlib import Path
from typing import Any

from bot.constants import TeamStatus


class DataStore:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init()
        self.migrate()

    def init(self) -> None:
        self.conn.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS team_users (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                warns INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                rank_position INTEGER DEFAULT -1,
                team_status TEXT DEFAULT '{TeamStatus.INACTIVE.value}',
                banned INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                log_general_channel_id TEXT,
                log_warn_channel_id TEXT,
                log_ban_channel_id TEXT,
                log_kick_channel_id TEXT,
                log_rank_channel_id TEXT,
                log_points_channel_id TEXT,
                dashboard_channel_id TEXT,
                team_role_id TEXT,
                admin_role_id TEXT,
                rank_roles_json TEXT DEFAULT '[]',
                auto_rankups INTEGER DEFAULT 0,
                auto_ban_limit INTEGER DEFAULT 3,
                auto_rank_points INTEGER DEFAULT 100
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                actor_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                note TEXT NOT NULL,
                actor_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def migrate(self) -> None:
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(guild_settings)").fetchall()]
        if "auto_rank_points" not in cols:
            self.conn.execute("ALTER TABLE guild_settings ADD COLUMN auto_rank_points INTEGER DEFAULT 100")
            self.conn.commit()

    @staticmethod
    def _to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def ensure_guild_settings(self, guild_id: int) -> None:
        exists = self.conn.execute("SELECT guild_id FROM guild_settings WHERE guild_id=?", (str(guild_id),)).fetchone()
        if not exists:
            self.conn.execute("INSERT INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
            self.conn.commit()

    def get_guild_settings(self, guild_id: int) -> dict[str, Any]:
        self.ensure_guild_settings(guild_id)
        row = self.conn.execute("SELECT * FROM guild_settings WHERE guild_id=?", (str(guild_id),)).fetchone()
        data = dict(row)
        data["auto_rankups"] = bool(data["auto_rankups"])
        data["rank_roles"] = json.loads(data["rank_roles_json"] or "[]")
        return data

    def update_guild_settings(self, guild_id: int, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_guild_settings(guild_id)
        merged = {**current, **patch}
        self.conn.execute(
            """
            UPDATE guild_settings SET
              log_general_channel_id=?, log_warn_channel_id=?, log_ban_channel_id=?,
              log_kick_channel_id=?, log_rank_channel_id=?, log_points_channel_id=?,
              dashboard_channel_id=?, team_role_id=?, admin_role_id=?, rank_roles_json=?,
              auto_rankups=?, auto_ban_limit=?, auto_rank_points=?
            WHERE guild_id=?
            """,
            (
                merged.get("log_general_channel_id"),
                merged.get("log_warn_channel_id"),
                merged.get("log_ban_channel_id"),
                merged.get("log_kick_channel_id"),
                merged.get("log_rank_channel_id"),
                merged.get("log_points_channel_id"),
                merged.get("dashboard_channel_id"),
                merged.get("team_role_id"),
                merged.get("admin_role_id"),
                json.dumps(merged.get("rank_roles", [])),
                1 if merged.get("auto_rankups") else 0,
                int(merged.get("auto_ban_limit", 3)),
                int(merged.get("auto_rank_points", 100)),
                str(guild_id),
            ),
        )
        self.conn.commit()
        return self.get_guild_settings(guild_id)

    def ensure_user(self, guild_id: int, user_id: int) -> None:
        exists = self.conn.execute(
            "SELECT user_id FROM team_users WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id))
        ).fetchone()
        if not exists:
            self.conn.execute("INSERT INTO team_users (guild_id, user_id) VALUES (?, ?)", (str(guild_id), str(user_id)))
            self.conn.commit()

    def get_user(self, guild_id: int, user_id: int) -> dict[str, Any]:
        self.ensure_user(guild_id, user_id)
        row = self.conn.execute(
            "SELECT * FROM team_users WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id))
        ).fetchone()
        return dict(row)

    def update_user(self, guild_id: int, user_id: int, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_user(guild_id, user_id)
        merged = {**current, **patch}
        self.conn.execute(
            """
            UPDATE team_users
            SET warns=?, points=?, rank_position=?, team_status=?, banned=?
            WHERE guild_id=? AND user_id=?
            """,
            (
                int(merged["warns"]),
                int(merged["points"]),
                int(merged["rank_position"]),
                merged["team_status"],
                1 if merged["banned"] else 0,
                str(guild_id),
                str(user_id),
            ),
        )
        self.conn.commit()
        return self.get_user(guild_id, user_id)

    def list_team_users(self, guild_id: int, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM team_users WHERE guild_id=? AND team_status=? ORDER BY points DESC",
                (str(guild_id), status),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM team_users WHERE guild_id=? ORDER BY points DESC", (str(guild_id),)
            ).fetchall()
        return [dict(r) for r in rows]

    def add_history(self, guild_id: int, user_id: int, action: str, reason: str | None, actor_id: int | None) -> None:
        self.conn.execute(
            "INSERT INTO history (guild_id, user_id, action, reason, actor_id) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(user_id), action, reason, str(actor_id) if actor_id else None),
        )
        self.conn.commit()

    def get_history(self, guild_id: int, user_id: int, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM history WHERE guild_id=? AND user_id=? ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?",
            (str(guild_id), str(user_id), limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_note(self, guild_id: int, user_id: int, note: str, actor_id: int | None) -> None:
        self.conn.execute(
            "INSERT INTO user_notes (guild_id, user_id, note, actor_id) VALUES (?, ?, ?, ?)",
            (str(guild_id), str(user_id), note, str(actor_id) if actor_id else None),
        )
        self.conn.commit()

    def get_notes(self, guild_id: int, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM user_notes WHERE guild_id=? AND user_id=? ORDER BY datetime(created_at) DESC LIMIT ?",
            (str(guild_id), str(user_id), limit),
        ).fetchall()
        return [dict(r) for r in rows]
