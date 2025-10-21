FROM python:3.13-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock README.md ./
RUN uv pip install --system .
COPY src/mcp_server_research/server.py .
EXPOSE 8001
CMD ["uv", "run", "server.py"]
