from contextlib import AsyncExitStack
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as mcpTool
from typing import List, TypedDict, Any, cast
import nest_asyncio
import os
import json
import google.genai as genai
from google.genai import types
from .adapter.tool_schema_converter import convert_schema


nest_asyncio.apply()

load_dotenv()

class MCP_Chatbot:

    def __init__(self) -> None:
        # Initialize session and client objects
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[mcpTool] = []
        self.tool_to_session: dict[str, ClientSession] = {}

        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    async def process_query(self, query: str) -> None:
        # Create Gemini tools
        gemini_tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description or '',
                        parameters=convert_schema(tool.inputSchema)
                    )
                ]
            ) for tool in self.available_tools
        ]
        toolConfig = types.GenerateContentConfig(
            tools=gemini_tools)  # type: ignore

        contents = []
        user_prompt_content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=query)],
        )
        contents.append(user_prompt_content)

        # Generate content with tools
        response = self.gemini_client.models.generate_content(
            model=self.model,
            contents=contents,
            config=toolConfig
        )

        # Loop until no more function calls (max 10 iterations)
        max_iterations = 10
        iteration = 0
        while response.candidates and response.function_calls and iteration < max_iterations:
            iteration += 1
            for function_call in response.function_calls:
                tool_name = function_call.name
                if not tool_name:
                    continue

                tool_args = dict(
                    function_call.args) if function_call.args else {}
                print(f"Calling tool {tool_name} with args {tool_args}")

                try:
                    # Call the MCP tool
                    if tool_name in self.tool_to_session:
                        session = self.tool_to_session[tool_name]
                        mcp_result = await session.call_tool(tool_name, arguments=tool_args)

                        function_response_part = types.Part.from_function_response(
                            name=tool_name,
                            response={'content': mcp_result.content},
                        )
                        contents.append(types.Content(
                            role='tool', parts=[function_response_part]
                        ))
                except Exception as e:
                    # Handle error case
                    error_response = {'error': str(e)}
                    function_response_part = types.Part.from_function_response(
                        name=tool_name,
                        response=error_response,
                    )
                    contents.append(types.Content(
                        role='tool', parts=[function_response_part]
                    ))
            
            # Generate next response
            response = self.gemini_client.models.generate_content(
                model=self.model,
                contents=contents,
                config=toolConfig
            )
        
        # Print final response
        if iteration >= max_iterations:
            print(f"Warning: Stopped after {max_iterations} tool calls to prevent infinite loop")
        print(response.text)


    async def chat_loop(self) -> None:
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print(f"Using GEMINI API with model: {self.model}")
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

    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server."""
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.sessions.append(session)

            # List available tools for this session
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [
                  t.name for t in tools])

            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append(tool)

        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        try:
            with open("src/mcp_chatbot/server_config.json", "r") as file:
                data = json.load(file)

            servers = data.get("mcpServers", {})

            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise

    async def cleanup(self):
        """Cleanly close all resources using AsyncExitStack."""
        await self.exit_stack.aclose()
