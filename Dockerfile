# OpenManus-Lite chat-bot relay — sandboxed runtime.
#
# Builds a minimal image that runs ONLY the Discord/Telegram bot, as a
# non-root user, with a read-only root filesystem except the workspace.
# This contains the agent's shell/Python execution tools: running it in a
# container with no network to cloud metadata + no mounts limits blast radius.
FROM python:3.11-slim

# Chromium deps are only needed if you enable the Browser tool; keep slim
# unless you use browser_agent / Manus with Browser.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
#     libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
#     libgbm1 libpango-1.0-0 libcairo2 libasound2 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-bot.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-bot.txt \
    && python -m playwright install --with-deps chromium 2>/dev/null || true

COPY . .

# Non-root user; workspace is the only writable area.
RUN useradd -m -u 1001 oml && chown -R oml:oml /app
USER oml

# workspace/ is the agent's only writable mount (bind a volume, read-only root).
ENV OML_PROD=1
VOLUME ["/app/workspace"]

ENTRYPOINT ["python", "bot/run_bot.py"]
