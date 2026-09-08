from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool()
def fail() -> str:
    """Always raises, to test MCPAdapter's error handling."""
    raise ValueError("simulated tool failure")


if __name__ == "__main__":
    mcp.run()
