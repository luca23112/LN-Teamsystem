# FiveM TeamSystem Discord Bot (Python)

Vollständig auf **Python (discord.py 2.x)** umgeschriebener Teamverwaltungs-Bot für FiveM-Server.

## Features

- Slash-Commands (`/team ...`, `/uprank`, `/downrank`, `/team-dashboard`, `/settings team ...`)
- SQLite-Datenbank (inkl. Migration)
- Rollenbasiertes Rechte-System (Team/Admin)
- Logging je Aktionstyp
- Rank-System (manuell + optional automatisch über Punkte)
- Teamnotizen, Teamstatus, Teamliste, Warn-Reset
- Dashboard mit Buttons + Pagination

## Projektstruktur

```txt
bot/
  cogs/
    dashboard.py
    rank.py
    settings.py
    team.py
  constants.py
  database.py
  logging_service.py
  main.py
  permissions.py
  team_logic.py
.env.example
requirements.txt
README.md
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## .env konfigurieren

- `DISCORD_TOKEN` = Bot Token
- `GUILD_ID` = Test-Server ID (optional; für schnelles Guild-Sync)
- `DB_PATH` = SQLite-Datei (optional)

## Starten

```bash
python -m bot.main
```

## Wichtige Commands

### Team

- `/team add user:@user`
- `/team kick user:@user grund:<grund>`
- `/team warn user:@user grund:<grund>`
- `/team resetwarns user:@user`
- `/team up user:@user punkte:<zahl> grund:<grund>`
- `/team down user:@user punkte:<zahl> grund:<grund>`
- `/team setstatus user:@user status:active|inactive|urlaub`
- `/team note user:@user text:<notiz>`
- `/team notes user:@user`
- `/team list status:<optional>`
- `/team ban user:@user grund:<grund>`
- `/team unban user:@user`

### Rank

- `/uprank user:@user`
- `/downrank user:@user`

### Dashboard

- `/team-dashboard user:@user`

### Settings

- `/settings team set-logchannel typ:<general|warn|ban|kick|rank|points> channel:#channel`
- `/settings team set-dashboard channel:#channel`
- `/settings team set-role typ:<team|admin> rolle:@rolle`
- `/settings team set-autoban limit:<zahl>`
- `/settings team set-auto-rank-points punkte:<zahl>`
- `/settings team rank-add position:<zahl> rolle:@rolle name:<optional>`
- `/settings team rank-remove position:<zahl>`
- `/settings team rank-toggle-auto aktiv:<true|false>`
- `/settings team show`
