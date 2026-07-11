"""OpenManus-Lite chat-bot relay for Discord and Telegram.

Relays inbound chat messages to the OpenManus-Lite agent and streams the
final answer back to the same chat. The agent itself runs in-process; the
bot is only a thin bridge.

Configuration (environment variables):
  DISCORD_BOT_TOKEN    Discord bot token (omit to disable Discord)
  TELEGRAM_BOT_TOKEN   Telegram bot token (omit to disable Telegram)
  OML_MODE             "single" (default, Manus) or "multi" (Supervisor)
  ALLOWED_DISCORD_GUILDS   comma-separated guild IDs (omit = all guilds)
  ALLOWED_TELEGRAM_USERS   comma-separated Telegram user IDs (omit = anyone)
  OML_CONFIG           path to config.toml (default: config/config.toml)

Run:
  python bot/run_bot.py                 # both platforms if tokens set
  python bot/run_bot.py --discord-only
  python bot/run_bot.py --telegram-only --mode multi
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Make the repo root importable regardless of CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import config  # noqa: E402  (loads config.toml)


def get_mode() -> str:
    return os.environ.get("OML_MODE", "single").lower()


def build_agent():
    """Create a fresh agent per task so memory/state never bleed across chats."""
    mode = get_mode()
    if mode == "multi":
        from app.agent.multi import Supervisor

        return Supervisor()
    from app.agent.manus import Manus

    return Manus()


async def run_agent(prompt: str) -> str:
    agent = build_agent()
    try:
        return await agent.run(prompt)
    except Exception as e:  # surface errors to chat instead of crashing
        return f"⚠️ Agent error: {type(e).__name__}: {e}"
    finally:
        try:
            await agent.cleanup()
        except Exception:
            pass


def chunk(text: str, limit: int):
    """Split long text into <=limit-char chunks on line boundaries."""
    if not text:
        return ["(empty result)"]
    if len(text) <= limit:
        return [text]
    out, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            if cur:
                out.append(cur)
            cur = line
            while len(cur) > limit:
                out.append(cur[:limit])
                cur = cur[limit:]
        else:
            cur = (cur + "\n" + line) if cur else line
    if cur:
        out.append(cur)
    return out


# --------------------------------------------------------------------------- #
# Discord
# --------------------------------------------------------------------------- #
async def run_discord(token: str, allowed_guilds: set[int]):
    import discord
    from discord.ext import commands

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    locks: dict[int, asyncio.Lock] = {}

    @bot.event
    async def on_ready():
        print(f"[discord] logged in as {bot.user} (guilds: {len(bot.guilds)})")

    @bot.event
    async def on_message(msg: discord.Message):
        if msg.author == bot.user:
            return
        if msg.guild and allowed_guilds and msg.guild.id not in allowed_guilds:
            return
        if not msg.content.strip():
            return

        lock = locks.setdefault(msg.channel.id, asyncio.Lock())
        async with lock:
            async with msg.channel.typing():
                result = await run_agent(msg.content)
            for part in chunk(result, 1900):
                await msg.channel.send(part)

    await bot.start(token)


# --------------------------------------------------------------------------- #
# Telegram
# --------------------------------------------------------------------------- #
async def run_telegram(token: str, allowed_users: set[int]):
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    locks: dict[int, asyncio.Lock] = {}

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        user_id = update.effective_user.id
        if allowed_users and user_id not in allowed_users:
            await update.message.reply_text("🚫 Unauthorized.")
            return
        chat_id = update.effective_chat.id
        lock = locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            result = await run_agent(update.message.text)
        for part in chunk(result, 4000):
            await update.message.reply_text(part)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("OpenManus-Lite ready. Send a task.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("[telegram] polling...")
    await app.run_polling()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="OpenManus-Lite chat relay.")
    parser.add_argument("--discord-only", action="store_true")
    parser.add_argument("--telegram-only", action="store_true")
    parser.add_argument("--mode", choices=["single", "multi"], default=None,
                        help="override OML_MODE (single|multi)")
    args = parser.parse_args()

    if args.mode:
        os.environ["OML_MODE"] = args.mode

    dc_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    if args.discord_only:
        tg_token = ""
    if args.telegram_only:
        dc_token = ""

    if not dc_token and not tg_token:
        print("❌ Set DISCORD_BOT_TOKEN and/or TELEGRAM_BOT_TOKEN (or use --discord-only/--telegram-only).")
        sys.exit(1)

    guilds = {int(g) for g in os.environ.get("ALLOWED_DISCORD_GUILDS", "").split(",") if g.strip()}
    users = {int(u) for u in os.environ.get("ALLOWED_TELEGRAM_USERS", "").split(",") if u.strip()}

    print(f"[bot] mode={get_mode()}, discord={'on' if dc_token else 'off'}, telegram={'on' if tg_token else 'off'}")

    async def serve():
        tasks = []
        if dc_token:
            tasks.append(run_discord(dc_token, guilds))
        if tg_token:
            tasks.append(run_telegram(tg_token, users))
        await asyncio.gather(*tasks)

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\n[bot] stopped.")


if __name__ == "__main__":
    main()
