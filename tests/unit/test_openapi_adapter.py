import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from runtrail.toolkit.openapi_adapter import OpenAPIAdapter

_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "test", "version": "1.0"},
    "paths": {
        "/add": {
            "get": {
                "operationId": "add",
                "parameters": [
                    {"name": "a", "in": "query", "schema": {"type": "integer"}},
                    {"name": "b", "in": "query", "schema": {"type": "integer"}},
                ],
            }
        },
        "/items/{item_id}": {
            "get": {
                "operationId": "getItem",
                "parameters": [{"name": "item_id", "in": "path", "schema": {"type": "string"}}],
            }
        },
        "/echo": {
            "post": {
                "operationId": "echo",
                "requestBody": {"content": {"application/json": {}}},
            }
        },
    },
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/add":
            query = parse_qs(parsed.query)
            body = {"sum": int(query["a"][0]) + int(query["b"][0])}
        elif parsed.path.startswith("/items/"):
            body = {"item_id": parsed.path.removeprefix("/items/")}
        else:
            self.send_response(404)
            self.end_headers()
            return
        self._send_json(body)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        self._send_json({"echoed": payload})

    def _send_json(self, body: dict):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args):
        pass


def _start_server() -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_call_resolves_query_parameters_against_a_real_server():
    server = _start_server()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        adapter = OpenAPIAdapter(_SPEC, "add", base_url=base_url)

        result = adapter.call(a=2, b=3)

        assert result == {"sum": 5}
    finally:
        server.shutdown()


def test_call_resolves_path_parameters():
    server = _start_server()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        adapter = OpenAPIAdapter(_SPEC, "getItem", base_url=base_url)

        result = adapter.call(item_id="abc123")

        assert result == {"item_id": "abc123"}
    finally:
        server.shutdown()


def test_call_sends_a_json_request_body():
    server = _start_server()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        adapter = OpenAPIAdapter(_SPEC, "echo", base_url=base_url)

        result = adapter.call(body={"hello": "world"})

        assert result == {"echoed": {"hello": "world"}}
    finally:
        server.shutdown()
