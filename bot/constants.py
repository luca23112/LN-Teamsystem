from enum import StrEnum


class LogType(StrEnum):
    GENERAL = "general"
    WARN = "warn"
    BAN = "ban"
    KICK = "kick"
    RANK = "rank"
    POINTS = "points"


class TeamStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    VACATION = "urlaub"
