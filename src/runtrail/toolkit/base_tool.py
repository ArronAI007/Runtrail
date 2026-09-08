from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Interface every Tool adapter (MCP / OpenAPI / mock) implements."""

    name: str

    @abstractmethod
    def call(self, **kwargs: Any) -> Any:
        """Invoke the tool and return its result."""
