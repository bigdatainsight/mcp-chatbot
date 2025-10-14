"""Main entry point for the MCP chatbot."""

import asyncio
from .chatbot import MCP_Chatbot


async def cli():
    """Main function to run the chatbot."""
    # Example usage
    chatbot = MCP_Chatbot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()


def main():
    """Entry point for the CLI script."""
    asyncio.run(cli())

if __name__ == "__main__":
    main()
