"""A local stand-in for OpenRouter's chat-completions endpoint."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StubLLM:
    def __init__(self, replies: list[dict]):
        self.replies = list(replies)
        self.requests: list[dict] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                stub.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                reply = stub.replies.pop(0) if len(stub.replies) > 1 else stub.replies[0]
                payload = json.dumps({
                    "id": f"stub-{len(stub.requests)}",
                    "object": "chat.completion",
                    "model": body.get("model"),
                    "choices": [{
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(reply)},
                    }],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
