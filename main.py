"""Application entry point."""
import asyncio

from app.agent.manus import Manus
from app.logger import logger


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
    asyncio.run(main())
