"""Main entry point for the MCP chatbot."""

import asyncio
from .chatbot import MCP_Chatbot


async def cli():
    """Main function to run the chatbot."""
    # Example usage
    chatbot = MCP_Chatbot()
    await chatbot.connect_to_server_and_run()


def main():
    """Entry point for the CLI script."""
    asyncio.run(cli())

if __name__ == "__main__":
    main()
