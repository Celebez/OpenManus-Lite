"""Application entry point."""
import asyncio
import sys

from app.agent.manus import Manus
from app.config import config
from app.logger import logger
from app.setup import config_needs_setup, run_setup


async def main(prompt: str = None):
    agent = Manus()
    try:
        prompt = prompt or input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return
        logger.warning("Processing your request...")
        result = await agent.run(prompt)
        logger.info("Request processing completed.")
        print("\n=== RESULT ===\n" + result)
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        run_setup()
        sys.exit(0)

    # Auto-run interactive setup if no usable config exists (Hermes-style).
    try:
        if config_needs_setup():
            print("No API configuration found. Starting setup...\n")
            run_setup()
            # restart interpreter config by re-importing
            import importlib
            import app.config as _cfg

            importlib.reload(_cfg)
            config = _cfg.config
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

    asyncio.run(main())
