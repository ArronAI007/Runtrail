from typing import Any

from runtrail.toolkit.base_tool import BaseTool


class MCPAdapter(BaseTool):
    """Calls one tool on an MCP server over stdio. Launches the server process
    fresh per call (no persistent session) — simple and stateless, at the
    cost of a subprocess-startup per call. Requires the 'mcp' extra:
    pip install 'runtrail[mcp]' (pinned to the mcp 1.x client API).
    """

    def __init__(self, command: list[str], tool_name: str, *, default_args: dict | None = None):
        self.name = tool_name
        self.command = command
        self._default_args = default_args or {}

    def call(self, **kwargs: Any) -> Any:
        try:
            import anyio
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise ImportError(
                "MCPAdapter requires the 'mcp' extra: pip install 'runtrail[mcp]'"
            ) from exc

        async def _call() -> Any:
            params = StdioServerParameters(command=self.command[0], args=list(self.command[1:]))
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(self.name, {**self._default_args, **kwargs})

        result = anyio.run(_call)

        text = "".join(getattr(part, "text", "") for part in result.content)
        if result.isError:
            raise RuntimeError(f"MCP tool '{self.name}' returned an error: {text}")

        structured = getattr(result, "structuredContent", None)
        return structured if structured is not None else text
