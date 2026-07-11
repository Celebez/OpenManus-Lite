# Chat-bot Relay (Discord + Telegram)

OpenManus-Lite can be driven from Discord or Telegram. The bot is a thin
bridge: it receives a message, runs `OpenManus-Lite.run_agent(prompt)`
in-process, and streams the answer back to the same chat.

## Install bot deps (optional)

```bash
pip install -r requirements-bot.txt
```

This adds `discord.py` and `python-telegram-bot`. The core framework does
**not** require them.

## Configure

Set environment variables (never commit tokens — use a `.env` or your
process manager):

```bash
export DISCORD_BOT_TOKEN="..."        # omit to disable Discord
export TELEGRAM_BOT_TOKEN="..."       # omit to disable Telegram
export OML_MODE="single"              # "single" (Manus) or "multi" (Supervisor)
export ALLOWED_DISCORD_GUILDS="1234567890"   # optional, comma-separated
export ALLOWED_TELEGRAM_USERS="555123"       # optional, comma-separated user IDs
```

- Discord needs the **Message Content Intent** enabled in the Developer Portal.
- Telegram: talk to `@BotFather` to create a bot and get the token.

## Run

```bash
python bot/run_bot.py                 # both, if both tokens set
python bot/run_bot.py --discord-only
python bot/run_bot.py --telegram-only --mode multi
```

## Behaviour

- Each chat (channel / Telegram chat) gets its **own lock**, so concurrent
  users don't interleave agent runs.
- A **fresh agent** is built per task, so memory/state never bleed across chats.
- Long answers are split to respect Discord (1900) / Telegram (4000) limits.
- Agent errors are caught and returned as a chat message — the bot keeps running.
