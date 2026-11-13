"""A local stand-in for the Claude Code CLI, so the tests need no login or network.

`FakeClaude(tmp_path, monkeypatch, replies)` writes an executable `claude`
and points $CLAUDE_BIN at it. It speaks the protocol BAML's ClaudeCodeClient
uses: one stream-json user message on stdin, JSONL events on stdout ending
in a `result` event that carries `structured_output`. Each `claude -p` call
is logged (argv, cwd and the prompt text) and answers with the next reply,
the last one repeating. `claude auth status` reports logged in unless
`logged_in=False`.
"""

import json
import sys
from pathlib import Path

SCRIPT = r'''
import json, os, sys
from pathlib import Path

state = Path(os.environ["FAKE_CLAUDE_STATE"])
config = json.loads((state / "config.json").read_text())
args = sys.argv[1:]
if args[:2] == ["auth", "status"]:
    print(json.dumps({"loggedIn": config["logged_in"]}))
    sys.exit(0 if config["logged_in"] else 1)
assert args[0] == "-p", args
message = json.loads(sys.stdin.readline())
prompt = "".join(b["text"] for b in message["message"]["content"] if b["type"] == "text")
calls = state / "calls.jsonl"
n = len(calls.read_text().splitlines()) if calls.exists() else 0
with calls.open("a") as f:
    f.write(json.dumps({"argv": args, "cwd": os.getcwd(), "prompt": prompt}) + "\n")
if config["exit_code"]:
    sys.exit(config["exit_code"])
print(json.dumps({"type": "system", "subtype": "init", "session_id": "fake"}))
reply = config["replies"][min(n, len(config["replies"]) - 1)]
if config["is_error"]:
    result = {"type": "result", "subtype": "error_during_execution", "is_error": True, "result": reply}
else:
    result = {"type": "result", "subtype": "success", "is_error": False,
              "result": json.dumps(reply), "structured_output": reply, "session_id": "fake",
              "usage": {"input_tokens": 1, "output_tokens": 1}}
print(json.dumps(result))
'''


class FakeClaude:
    def __init__(self, tmp_path: Path, monkeypatch, replies: list, logged_in=True, exit_code=0, is_error=False):
        self.state = tmp_path / "fake-claude"
        self.state.mkdir()
        (self.state / "fake_claude_impl.py").write_text(SCRIPT)
        (self.state / "config.json").write_text(json.dumps(
            {"replies": replies, "logged_in": logged_in, "exit_code": exit_code, "is_error": is_error}
        ))
        exe = self.state / "claude"
        # /bin/sh exists in the Nix build sandbox; /usr/bin/env may not.
        exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{self.state / "fake_claude_impl.py"}" "$@"\n')
        exe.chmod(0o755)
        monkeypatch.setenv("CLAUDE_BIN", str(exe))
        monkeypatch.setenv("FAKE_CLAUDE_STATE", str(self.state))

    @property
    def calls(self) -> list[dict]:
        log = self.state / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
