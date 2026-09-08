from collections.abc import Callable
from typing import Any

from runtrail.toolkit.base_tool import BaseTool


class LocalFunctionTool(BaseTool):
    """Wraps a plain Python callable as a BaseTool — for tools that don't need
    a network hop (MCP/OpenAPI) or a sandbox (CodeExecTool), just a function.
    """

    def __init__(self, name: str, fn: Callable[..., Any]):
        self.name = name
        self._fn = fn

    def call(self, **kwargs: Any) -> Any:
        return self._fn(**kwargs)
