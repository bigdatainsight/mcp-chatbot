# Research MCP Server

A Model Context Protocol server that provides academic paper search and information retrieval capabilities from arXiv. This server enables LLMs to search for research papers by topic and retrieve detailed information about specific papers.

> [!NOTE]
> This server searches arXiv.org for academic papers and stores paper information locally for quick retrieval. All data is publicly available from arXiv.

The server stores paper information in JSON format organized by search topics, allowing for efficient retrieval and cross-referencing of academic papers.

> [!INFO]
> This server runs on SSE (Server-Sent Events) transport on port 8001 by default, providing real-time communication capabilities.

### Available Tools

- `search_papers` - Searches arXiv for papers on a given topic and stores their information locally.
    - `topic` (string, required): The research topic to search for
    - `max_results` (integer, optional): Maximum number of results to retrieve (default: 5)

- `extract_info` - Retrieves detailed information about a specific paper by its arXiv ID.
    - `paper_id` (string, required): The arXiv paper ID (e.g., "2301.12345")

### Prompts

- **generate_search_prompt**
  - Generate a comprehensive prompt for Claude to find and discuss academic papers on a specific topic
  - Arguments:
    - `topic` (string, required): Research topic to search for
    - `num_papers` (integer, optional): Number of papers to search for (default: 5)
  - Type `/prompts` to list all the available prompts
  - Type `/prompt <name> <arg1=value1> <arg2=value2>` to call a specific prompt

### Resources

- **papers://folders**
  - Lists all available topic folders in the papers directory
  - Provides a markdown list of topics that have been searched and have stored papers
  - Type `@folders` to list topics

- **papers://{topic}**
  - Get detailed information about papers on a specific topic
  - Returns formatted markdown with paper details including titles, authors, summaries, and PDF links
  - Arguments:
    - `topic` (string, required): The research topic to retrieve papers for
  - Type `@<topic>` to show details of the topic

## Installation

### Using docker (recommended)

```bash
docker buildx build . -t github.com/bigdatainsight/mcp-server-research:latest
docker run --rm -p 8001:8001 --name research-server -d github.com/bigdatainsight/mcp-server-research:latest
```

### Using uv

When using [`uv`](https://docs.astral.sh/uv/) from the project directory:

```
uv run mcp-server-research
```

The server will start on `http://localhost:8001` using streamable http transport.

### Using Python

Alternatively you can run the server directly:

```
python -m mcp_server_research.server
```

The server will be available at `http://localhost:8001`.

Make sure you have the required dependencies installed:

```
pip install arxiv mcp python-dotenv
```

## Configuration
<details>
<summary>Using docker</summary>

```json
{
  "mcpServers": {
    "research": {
      "url": "http://localhost:8001"
    }
  }
}
```
</details>


### Customization - Server Configuration

The server runs on streamable http transport by default on port 8001. You can modify the port by changing the `port` parameter in the FastMCP initialization.

### Customization - Data Storage

By default, the server stores paper information in the `data/papers/` directory, organized by search topics. Each topic gets its own subdirectory with a `papers_info.json` file containing the paper metadata.

### Customization - Search Results

You can customize the maximum number of search results by modifying the `max_results` parameter when calling the `search_papers` tool. The default is 5 papers per search.

## Debugging

You can use the MCP inspector to debug the server.

Step 1: Start up server

```bash
docker run --rm -p 8001:8001 --name research-server -d github.com/bigdatainsight/mcp-server-research:latest
docker logs research-server
```

Step 2: Start up inspector

```bash
npx @modelcontextprotocol/inspector
```
Step 3: Configure the UI

```
Transport Type: Streamable HTTP

URL: http://localhost:8001

Connection Type: Direct
```
