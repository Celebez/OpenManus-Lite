# Chat-bot Relay (Discord + Telegram)

OpenManus-Lite can be driven from Discord or Telegram. The bot is a thin
bridge: it receives a message, runs `OpenManus-Lite.run_agent(prompt)`
in-process, and streams the answer back to the same chat.

> ⚠️ **Security**: the agent has shell + Python execution tools. Never expose
> the bot to untrusted users without (a) running it in a container/sandbox and
> (b) setting allow-lists. See **Hardening** below.

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
export ALLOWED_DISCORD_GUILDS="1234567890"   # REQUIRED in prod: comma-separated guild IDs
export ALLOWED_TELEGRAM_USERS="555123"       # REQUIRED in prod: comma-separated user IDs
export OML_PROD="1"                   # refuse to start if allow-lists are empty
```

- Discord needs the **Message Content Intent** enabled in the Developer Portal.
- Telegram: talk to `@BotFather` to create a bot and get the token.
- `ask_human` is **disabled** in bot mode (no interactive stdin — calling it
  would otherwise hang the bot forever).

## Run

```bash
python bot/run_bot.py                 # both, if both tokens set
python bot/run_bot.py --discord-only
python bot/run_bot.py --telegram-only --mode multi
```

## Hardening (recommended for any public exposure)

The agent can run arbitrary shell/Python. Contain it:

1. **Run in a container** — see `Dockerfile`. It runs as non-root, read-only
   root FS, only `workspace/` mounted writable, and no metadata-network access.
2. **Set allow-lists** — `ALLOWED_DISCORD_GUILDS` / `ALLOWED_TELEGRAM_USERS`.
   With `OML_PROD=1` the bot **refuses to start** if both are empty.
3. **Never mount secrets** into the container's workspace.

```bash
docker build -t oml-bot .
docker run --rm -e DISCORD_BOT_TOKEN=... -e TELEGRAM_BOT_TOKEN=... \
  -e OML_PROD=1 -e ALLOWED_TELEGRAM_USERS=555123 \
  -v "$(pwd)/workspace:/app/workspace" oml-bot
```

## Behaviour

- Each chat (channel / Telegram chat) gets its **own lock**, so concurrent
  users don't interleave agent runs.
- A **fresh agent** is built per task, so memory/state never bleed across chats.
- Long answers are split to respect Discord (1900) / Telegram (4000) limits.
- Agent errors are caught and returned as a chat message — the bot keeps running.
