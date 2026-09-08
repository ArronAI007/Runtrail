import json

import httpx
import pytest

from runtrail.agent.remote_agent import RemoteAgent


def test_run_posts_task_input_and_returns_json_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"output": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    agent = RemoteAgent("http://agent.test/invoke", client=client)

    result = agent.run("hello")

    assert captured["body"] == {"input": "hello"}
    assert result == {"output": "ok"}


def test_run_raises_on_error_status():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    agent = RemoteAgent("http://agent.test/invoke", client=client)

    with pytest.raises(httpx.HTTPStatusError):
        agent.run("hello")
