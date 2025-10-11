from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio
import os
import json
from .research_mcp_server import execute_tool

nest_asyncio.apply()

load_dotenv()


class MCP_Chatbot:

    def __init__(self) -> None:
        # Initialize session and client objects
        self.session: ClientSession | None = None
        self.available_tools: List[dict] = []

        # Initialize client based on provider
        self.api_provider = os.getenv("API_PROVIDER", "openai").lower()

        if self.api_provider == "anthropic":
            import anthropic
            self.anthropic_client = anthropic.Anthropic()
            self.model = os.getenv(
                "ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
        elif self.api_provider == "openai":
            import openai
            self.openai_client = openai.OpenAI()
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif self.api_provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.gemini_client = genai.GenerativeModel(
                os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
            self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")

    async def process_query(self, query: str) -> None:
        if self.api_provider == "anthropic":
            await self.process_anthropic_query(query)
        elif self.api_provider == "gemini":
            await self.process_gemini_query(query)
        else:
            await self.process_openai_query(query)

    async def process_anthropic_query(self, query: str) -> None:
        messages = [{'role': 'user', 'content': query}]

        response = self.anthropic_client.messages.create(
            max_tokens=2024,
            model=self.model,
            tools=self.available_tools,  # type: ignore
            messages=messages  # type: ignore
        )

        process_query_loop = True
        while process_query_loop:
            assistant_content = []

            for content in response.content:
                if content.type == 'text':
                    print(content.text)
                    assistant_content.append(content)  # type: ignore
                    if len(response.content) == 1:
                        process_query_loop = False

                elif content.type == 'tool_use':
                    assistant_content.append(content)  # type: ignore
                    messages.append(
                        # type: ignore
                        {'role': 'assistant', 'content': assistant_content})

                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    print(f"Calling tool {tool_name} with args {tool_args}")

                    # result = execute_tool(tool_name, tool_args)
                    # Call a tool
                    # result = execute_tool(tool_name, tool_args): not anymore needed
                    # tool invocation through the client session
                    # type: ignore
                    result = await self.session.call_tool(tool_name, arguments=tool_args)

                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        }]
                    })  # type: ignore

                    response = self.anthropic_client.messages.create(
                        max_tokens=2024,
                        model=self.model,
                        tools=self.available_tools,
                        messages=messages
                    )

                    if len(response.content) == 1 and response.content[0].type == "text":
                        print(response.content[0].text)
                        process_query_loop = False

    async def process_openai_query(self, query: str) -> None:
        messages = [{'role': 'user', 'content': query}]

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.available_tools,
            max_tokens=2024
        )

        message = response.choices[0].message

        if message.tool_calls:
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print(f"Calling tool {tool_name} with args {tool_args}")

                result = execute_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            final_response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2024
            )
            print(final_response.choices[0].message.content)
        else:
            print(message.content)

    async def process_gemini_query(self, query: str) -> None:
        # Convert MCP tools to Gemini format - clean schema for Gemini
        def clean_schema(schema):
            cleaned = {}
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    cleaned[key] = {k: {kk: vv for kk, vv in v.items() if kk not in ["default", "title"]} for k, v in value.items()}
                elif key not in ["default", "title"]:
                    cleaned[key] = value
            return cleaned

        gemini_tools = [{
            "function_declarations": [{
                "name": tool["name"],
                "description": tool["description"],
                "parameters": clean_schema(tool["input_schema"])
            } for tool in self.available_tools]
        }]

        response = self.gemini_client.generate_content(
            query,
            tools=gemini_tools
        )

        # Check if response has function calls
        has_function_call = False
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                has_function_call = True
                function_call = part.function_call
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                print(f"Calling tool {tool_name} with args {tool_args}")

                result = execute_tool(tool_name, tool_args)

                final_response = self.gemini_client.generate_content([
                    {"role": "user", "parts": [query]},
                    {"role": "model", "parts": [part]},
                    {"role": "user", "parts": [{"function_response": {
                        "name": tool_name, "response": {"result": result}}}]}
                ])
                print(final_response.text)
                break

        if not has_function_call:
            print(response.text)

    async def chat_loop(self) -> None:
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print(f"Using {self.api_provider.upper()} API with model: {self.model}")
        print("Type your queries or 'quit' to exit.")

        try:
            while True:
                try:
                    query = input("\nQuery: ").strip()
                    if query.lower() == 'quit':
                        print("Exiting...")
                        break

                    await self.process_query(query)
                    print("\n")
                except Exception as e:
                    print(f"\nError: {str(e)}")
        except KeyboardInterrupt:
            pass
        finally:
            print("\nGoodbye!")

    async def connect_to_server_and_run(self) -> None:
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            # Optional command line arguments
            args=["run", "python", "-m", "mcp_chatbot.research_mcp_server"],
            env=None,  # Optional environment variables
        )

        # Launch the server as a subprocess & returns the read and write streams
        # read: the stream that the client will use to read msgs from the server
        # write: the stream that client will use to write msgs to the server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection
                await session.initialize()

                # List available tools
                response = await session.list_tools()

                tools = response.tools
                print("\nConnected to server with tools:",
                      [tool.name for tool in tools])

                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]

                await self.chat_loop()
