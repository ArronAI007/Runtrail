from typing import Any

from runtrail.toolkit.base_tool import BaseTool


class OpenAPIAdapter(BaseTool):
    """Calls one operation from an OpenAPI 3.x spec (JSON) as a BaseTool.

    Supports path/query parameters and a JSON request body — no $ref
    resolution across external files, no non-JSON media types, no auth
    beyond a static `headers` dict. For anything beyond that, write a
    LocalFunctionTool around your own client instead. Requires the 'remote'
    extra: pip install 'runtrail[remote]'.
    """

    def __init__(
        self,
        spec: dict,
        operation_id: str,
        *,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        self.name = operation_id
        self._path, self._method, self._operation = _find_operation(spec, operation_id)
        self._base_url = (base_url or _server_url(spec)).rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout

    @classmethod
    def from_url(
        cls,
        spec_url: str,
        operation_id: str,
        *,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> "OpenAPIAdapter":
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "OpenAPIAdapter requires the 'remote' extra: pip install 'runtrail[remote]'"
            ) from exc

        spec = httpx.get(spec_url, timeout=timeout).json()
        return cls(spec, operation_id, base_url=base_url, headers=headers, timeout=timeout)

    def call(self, **kwargs: Any) -> Any:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "OpenAPIAdapter requires the 'remote' extra: pip install 'runtrail[remote]'"
            ) from exc

        path = self._path
        query: dict[str, Any] = {}
        used_keys: set[str] = set()
        for param in self._operation.get("parameters", []):
            pname = param["name"]
            if pname not in kwargs:
                continue
            used_keys.add(pname)
            if param["in"] == "path":
                path = path.replace("{" + pname + "}", str(kwargs[pname]))
            elif param["in"] == "query":
                query[pname] = kwargs[pname]

        body = None
        if "requestBody" in self._operation:
            remaining = {k: v for k, v in kwargs.items() if k not in used_keys}
            body = remaining.get("body", remaining)

        response = httpx.request(
            self._method.upper(),
            f"{self._base_url}{path}",
            params=query,
            json=body,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        return response.json() if "application/json" in content_type else response.text


def _find_operation(spec: dict, operation_id: str) -> tuple[str, str, dict]:
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if operation.get("operationId") == operation_id:
                return path, method, operation
    raise ValueError(f"No operation with operationId '{operation_id}' found in the OpenAPI spec")


def _server_url(spec: dict) -> str:
    servers = spec.get("servers") or []
    return servers[0]["url"] if servers else ""
