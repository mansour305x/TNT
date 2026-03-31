# Whiteout Survival Discord Bot

Whiteout Survival Discord Bot that supports alliance management, event reminders and attendance tracking, gift code redemption, minister appointment planning and more. This bot is free, open source and self-hosted.

**This is the actively maintained and improved version of the original bot that was created and soon abandoned by Reloisback.**

## 🚀 Getting Started

To get started with the bot, head over to the [wiki](https://github.com/whiteout-project/bot/wiki) for instructions and other information.

If you have any issues with the bot, head over to the [common issues](https://github.com/whiteout-project/bot/wiki/Common-Issues) page or join our [discord server](https://discord.gg/apYByj6K2m) for support.

## Member Registration Portal

This repository now includes a standalone web portal for member registration in `member_portal/`.

Features:
- Fixed required inputs for member name and member ID.
- Dynamic dropdown fields managed from an admin control panel.
- Registered users can contribute new dropdown options.
- SQLite database persistence for users, dropdown setup, and member records.

Run locally:

```bash
pip install -r requirements.txt
python member_portal/app.py
```

Environment variables:
- `PORT`: HTTP port (default: `8080`)
- `PORTAL_SECRET_KEY`: session signing secret (set this in production)
- `PORTAL_ADMIN_PASSWORD`: default admin password used on first startup (default: `admin123`)
- `PORTAL_FULL_ADMIN_USERNAME`: full-control admin username (default: `mn9@hotmail.com`)
- `PORTAL_FULL_ADMIN_PASSWORD`: full-control admin password (default: `DANGER`)
