import sys
from pathlib import Path

import pytest

from runtrail.toolkit.mcp_adapter import MCPAdapter

_SERVER = str(Path(__file__).parent / "fixtures" / "mcp_server.py")


def test_call_returns_the_tool_result_from_a_real_mcp_server():
    adapter = MCPAdapter([sys.executable, _SERVER], "add")

    result = adapter.call(a=2, b=3)

    assert result == {"result": 5}


def test_call_raises_when_the_mcp_tool_errors():
    adapter = MCPAdapter([sys.executable, _SERVER], "fail")

    with pytest.raises(RuntimeError, match="simulated tool failure"):
        adapter.call()


def test_default_args_are_merged_with_call_kwargs():
    adapter = MCPAdapter([sys.executable, _SERVER], "add", default_args={"a": 10})

    result = adapter.call(b=5)

    assert result == {"result": 15}
