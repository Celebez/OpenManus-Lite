"""Application entry point."""
import argparse
import asyncio
import os
import sys

from app.config import config
from app.logger import logger
from app.setup import config_needs_setup, run_setup


async def main(prompt: str = None, use_supervisor: bool = False):
    if use_supervisor:
        from app.agent.multi import Supervisor

        agent = Supervisor()
        logger.info("Starting in multi-agent (Supervisor) mode.")
    else:
        from app.agent.manus import Manus

        agent = Manus()
        logger.info("Starting in single-agent (Manus) mode.")
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="OpenManus-Lite: a lightweight AI agent framework."
    )
    parser.add_argument("--setup", action="store_true", help="Run interactive setup wizard.")
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Use multi-agent Supervisor mode (routes to specialised sub-agents).",
    )
    parser.add_argument("--prompt", "-p", type=str, default=None, help="Task prompt (skip interactive input).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.setup:
        run_setup()
        sys.exit(0)

    # Auto-run interactive setup if no usable config exists.
    # Env-only mode: OML_API_KEY + OML_BASE_URL + OML_MODEL let you skip the
    # wizard entirely (zero file editing). If those are present we don't prompt.
    env_configured = all(
        os.environ.get(k) for k in ("OML_API_KEY", "OML_BASE_URL", "OML_MODEL")
    )
    try:
        if not env_configured and config_needs_setup():
            print("No API configuration found. Starting setup...\n")
            run_setup()
            # reload config so the freshly written file is picked up
            import importlib

            import app.config as _cfg

            importlib.reload(_cfg)
            config = _cfg.config
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

    asyncio.run(main(prompt=args.prompt, use_supervisor=args.multi))
