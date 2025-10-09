# MCP Chatbot

An AI-powered chatbot for searching and analyzing academic papers from arXiv. The chatbot uses function calling to interact with the arXiv API and provides intelligent responses about research papers.

## Features

- **Paper Search**: Search for academic papers on arXiv by topic
- **Paper Information Extraction**: Retrieve detailed information about specific papers
- **Multi-LLM Support**: Works with OpenAI, Anthropic Claude, and Google Gemini models
- **Function Calling**: Uses tool/function calling capabilities of modern LLMs
- **Local Storage**: Saves paper information locally for quick retrieval

## Supported LLM Providers

### OpenAI
- Models: GPT-4o-mini (default), GPT-4o, GPT-3.5-turbo
- Uses OpenAI's function calling format

### Anthropic Claude
- Models: Claude-3-7-sonnet-20250219 (default), Claude-3-haiku, Claude-3-opus
- Uses Anthropic's tool use format

### Google Gemini
- Models: Gemini-1.5-flash (default), Gemini-1.5-pro, Gemini-2.5-flash
- Uses Gemini's function declarations format

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mcp-chatbot
```

2. Install dependencies:
```bash
uv sync
```

3. Create a `.env` file with your API credentials:
```env
API_PROVIDER=gemini  # or openai, anthropic
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: specify models
GEMINI_MODEL=gemini-1.5-flash
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-7-sonnet-20250219
```

## Usage

Run the chatbot:
```bash
uv run mcp-chatbot
```

Example queries:
- "Find some computer science papers about machine learning"
- "Search for papers on quantum computing"
- "Get information about paper 2301.12345"

## Available Tools

### search_papers
Searches arXiv for papers on a given topic and stores their information locally.

**Parameters:**
- `topic` (string): The research topic to search for
- `max_results` (integer, optional): Maximum number of results (default: 5)

### extract_info
Retrieves detailed information about a specific paper by its arXiv ID.

**Parameters:**
- `paper_id` (string): The arXiv paper ID (e.g., "2301.12345")

## Development

Run tests:
```bash
uv run pytest -v
```

Debug in VS Code:
1. Set breakpoints in the code
2. Press F5 to start debugging
3. Use the debug configuration in `.vscode/launch.json`

## Current Implementation Disadvantages

### 1. **Tool Format Duplication**
- Each LLM provider requires different tool/function formats
- Currently maintains separate tool definitions (`toolList`, `toolList_gemini`)
- Leads to code duplication and maintenance overhead

### 2. **Provider-Specific Code Paths**
- Separate processing functions for each provider (`process_openai_query`, `process_anthropic_query`, `process_gemini_query`)
- Different response handling logic for each provider
- Makes adding new providers complex

### 3. **Limited Error Handling**
- Basic exception handling without provider-specific error recovery
- No retry mechanisms for API failures
- Limited validation of API responses

### 4. **Static Configuration**
- API provider is set at startup via environment variables
- Cannot switch providers during runtime
- No fallback mechanism if primary provider fails

### 5. **Tool Schema Limitations**
- Gemini doesn't support `default` values in schemas
- Manual schema cleaning required for different providers
- Type mapping inconsistencies (e.g., `string` vs `STRING`)

### 6. **Storage Implementation**
- Simple file-based storage without indexing
- No database integration for better querying
- Limited search capabilities across stored papers

### 7. **Conversation Context**
- No conversation history persistence
- Each query is processed independently
- No multi-turn conversation support with context

## Future Improvements

- Implement a unified tool interface with automatic format conversion
- Add provider abstraction layer
- Implement conversation history and context management
- Add database storage with full-text search
- Implement retry mechanisms and better error handling
- Add streaming responses for better user experience