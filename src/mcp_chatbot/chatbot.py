from contextlib import AsyncExitStack
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as mcpTool
from mcp.shared.exceptions import McpError
from typing import List, TypedDict, Any, cast
import nest_asyncio
import os
import json
import traceback
import google.genai as genai
from google.genai import types
from .adapter.tool_schema_converter import convert_schema


nest_asyncio.apply()

load_dotenv()

class MCP_Chatbot:

    def __init__(self) -> None:
        # Sessions dict maps tool/prompt names or resource URIs to MCP client sessions
        self.session_maps: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[mcpTool] = []
        # Prompts list for quick display
        self.available_prompts: List[dict] = []

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
                    if tool_name in self.session_maps:
                        session = self.session_maps[tool_name]
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
                    print(
                        f"Tool execution error: {type(e).__name__}: {str(e)}")
                    print(f"Traceback: {traceback.format_exc()}")
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

    async def get_resource(self, resource_uri):
        session = self.session_maps.get(resource_uri)

        # Fallback for papers URIs - try any papers resource session
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.session_maps.items():
                if uri.startswith("papers://"):
                    session = sess
                    break

        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return

        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource: {resource_uri}")
                print("Content:")
                print(result.contents[0].text)
            else:
                print("No content available.")
        except Exception as e:
            print(f"Error: {e}")

    async def list_prompts(self):
        """List all available prompts."""
        if not self.available_prompts:
            print("No prompts available.")
            return

        print("\nAvailable prompts:")
        for prompt in self.available_prompts:
            print(f"- {prompt['name']}: {prompt['description']}")
            if prompt['arguments']:
                print(f"  Arguments:")
                for arg in prompt['arguments']:
                    arg_name = arg.name if hasattr(
                        arg, 'name') else arg.get('name', '')
                    print(f"    - {arg_name}")

    async def execute_prompt(self, prompt_name, args):
        """Execute a prompt with the given arguments."""
        session = self.session_maps.get(prompt_name)
        if not session:
            print(f"Prompt '{prompt_name}' not found.")
            return

        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content

                # Extract text from content (handles different formats)
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, 'text'):
                    text = prompt_content.text
                else:
                    # Handle list of content items
                    text = " ".join(item.text if hasattr(item, 'text') else str(item)
                                    for item in prompt_content)

                print(f"\nExecuting prompt '{prompt_name}'...")
                await self.process_query(text)
        except Exception as e:
            print(f"Error: {e}")

    async def chat_loop(self) -> None:
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        print("Use @folders to see available topics")
        print("Use @<topic> to search papers in that topic")
        print("Use /prompts to list available prompts")
        print("Use /prompt <name> <arg1=value1> to execute a prompt")

        try:
            while True:
                try:
                    query = input("\nQuery: ").strip()
                    if query.lower() == 'quit':
                        print("Exiting...")
                        break

                    # Check for @resource syntax first
                    if query.startswith('@'):
                        # Remove @ sign
                        topic = query[1:]
                        if topic == "folders":
                            resource_uri = "papers://folders"
                        else:
                            resource_uri = f"papers://{topic}"
                        await self.get_resource(resource_uri)
                        continue

                    # Check for /command syntax
                    if query.startswith('/'):
                        parts = query.split()
                        command = parts[0].lower()

                        if command == '/prompts':
                            await self.list_prompts()
                        elif command == '/prompt':
                            if len(parts) < 2:
                                print(
                                    "Usage: /prompt <name> <arg1=value1> <arg2=value2>")
                                continue

                            prompt_name = parts[1]
                            args = {}

                            # Parse arguments
                            for arg in parts[2:]:
                                if '=' in arg:
                                    key, value = arg.split('=', 1)
                                    args[key] = value

                            await self.execute_prompt(prompt_name, args)
                        else:
                            print(f"Unknown command: {command}")
                        continue

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

            # List available tools for this session
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [
                  t.name for t in tools])

            for tool in tools:
                self.session_maps[tool.name] = session
                self.available_tools.append(tool)

            # List available prompts if supported
            try:
                prompts_response = await session.list_prompts()
                if prompts_response and prompts_response.prompts:
                    for prompt in prompts_response.prompts:
                        self.session_maps[prompt.name] = session
                        self.available_prompts.append({
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments
                        })
            except McpError as e:
                if "Method not found" in str(e):
                    print(f"  {server_name} does not support prompts")
                else:
                    raise

            # List available resources
            try:
                resources_response = await session.list_resources()
                if resources_response and resources_response.resources:
                    for resource in resources_response.resources:
                        resource_uri = str(resource.uri)
                        self.session_maps[resource_uri] = session
            except McpError as e:
                if "Method not found" in str(e):
                    print(f"  {server_name} does not support resources")
                else:
                    raise

        except Exception as e:
            print(f"{type(e).__name__}: {str(e)}")

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
