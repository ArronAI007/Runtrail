from typing import Any

from runtrail.agent.base import BaseAgent


class RemoteAgent(BaseAgent):
    """Calls an external Agent over HTTP (e.g. LangGraph, AutoGen, a custom service).

    POSTs {"input": task_input} to `endpoint` and returns the parsed JSON response
    as the output dict. Requires the 'remote' extra: pip install 'runtrail[remote]'.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        client: Any = None,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.headers = headers or {}
        self._client = client

    def run(self, task_input: Any) -> dict:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "RemoteAgent requires the 'remote' extra: pip install 'runtrail[remote]'"
            ) from exc

        client = self._client or httpx.Client(timeout=self.timeout)
        response = client.post(self.endpoint, json={"input": task_input}, headers=self.headers)
        response.raise_for_status()
        return response.json()
