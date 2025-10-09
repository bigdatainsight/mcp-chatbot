import os
import json
from dotenv import load_dotenv
from .tools import toolList, toolList_gemini, execute_tool

# Convert toolList to different formats for each provider
tools = [{
    "type": "function",
    "function": {
        "name": tool["name"],
        "description": tool["description"],
        "parameters": tool["input_schema"]
    }
} for tool in toolList]

load_dotenv()

# Initialize client based on provider
api_provider = os.getenv("API_PROVIDER", "openai").lower()

if api_provider == "anthropic":
    import anthropic
    anthropic_client = anthropic.Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
elif api_provider == "openai":
    import openai
    openai_client = openai.OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
elif api_provider == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_client = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
else:
    raise ValueError(f"Unsupported API provider: {api_provider}")

def process_query(query):
    if api_provider == "anthropic":
        process_anthropic_query(query)
    elif api_provider == "gemini":
        process_gemini_query(query)
    else:
        process_openai_query(query)

def process_anthropic_query(query):
    messages = [{'role': 'user', 'content': query}]

    response = anthropic_client.messages.create(
        max_tokens=2024,
        model=model,
        tools=tools,
        messages=messages
    )

    process_query_loop = True
    while process_query_loop:
        assistant_content = []

        for content in response.content:
            if content.type == 'text':
                print(content.text)
                assistant_content.append(content)
                if len(response.content) == 1:
                    process_query_loop = False

            elif content.type == 'tool_use':
                assistant_content.append(content)
                messages.append({'role': 'assistant', 'content': assistant_content})

                tool_id = content.id
                tool_args = content.input
                tool_name = content.name
                print(f"Calling tool {tool_name} with args {tool_args}")

                result = execute_tool(tool_name, tool_args)
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    }]
                })

                response = anthropic_client.messages.create(
                    max_tokens=2024,
                    model=model,
                    tools=tools,
                    messages=messages
                )

                if len(response.content) == 1 and response.content[0].type == "text":
                    print(response.content[0].text)
                    process_query_loop = False

def process_openai_query(query):
    messages = [{'role': 'user', 'content': query}]

    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
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

        final_response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2024
        )
        print(final_response.choices[0].message.content)
    else:
        print(message.content)

def process_gemini_query(query):
    response = gemini_client.generate_content(
        query,
        tools=[toolList_gemini]
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

            final_response = gemini_client.generate_content([
                {"role": "user", "parts": [query]},
                {"role": "model", "parts": [part]},
                {"role": "user", "parts": [{"function_response": {"name": tool_name, "response": {"result": result}}}]}
            ])
            print(final_response.text)
            break

    if not has_function_call:
        print(response.text)

def chat_loop():
    print(f"Using {api_provider.upper()} API with model: {model}")
    print("Type your queries or 'quit' to exit.")

    try:
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break

                process_query(query)
                print("\n")
            except Exception as e:
                print(f"\nError: {str(e)}")
    except KeyboardInterrupt:
        pass
    finally:
        print("\nGoodbye!")
        import sys
        sys.exit(0)