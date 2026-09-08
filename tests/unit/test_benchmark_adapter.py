import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from runtrail.dataset import BenchmarkAdapter


def test_from_jsonl_applies_field_map(tmp_path):
    path = tmp_path / "gaia.jsonl"
    path.write_text(
        json.dumps({"Question": "2+2?", "Final answer": "4"}) + "\n"
        + json.dumps({"Question": "capital of France?", "Final answer": "Paris"}) + "\n"
    )

    dataset = BenchmarkAdapter.from_jsonl(
        "gaia",
        path,
        field_map=lambda r: {"input": r["Question"], "ground_truth": r["Final answer"]},
    )

    assert len(dataset) == 2
    assert list(dataset) == [
        {"input": "2+2?", "ground_truth": "4"},
        {"input": "capital of France?", "ground_truth": "Paris"},
    ]


def test_from_url_fetches_and_parses_a_json_array():
    records = [{"input": "a", "ground_truth": "1"}, {"input": "b", "ground_truth": "2"}]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(records).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        dataset = BenchmarkAdapter.from_url("dummy", f"http://127.0.0.1:{port}/data.json")
    finally:
        server.shutdown()

    assert list(dataset) == records


def test_default_field_map_passes_through_input_and_ground_truth():
    dataset = BenchmarkAdapter("dummy", [{"input": "x", "ground_truth": "y", "extra": "ignored"}])

    assert list(dataset) == [{"input": "x", "ground_truth": "y"}]
