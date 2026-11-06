import json

from conftest import HELLO
from stub_llm import StubLLM
from updater.workflow import BamlClient, run


def plan_json(find):
    return {
        "attr": "hello",
        "current_version": "1.0",
        "target_version": "1.1",
        "needs_update": True,
        "edits": [{"path": HELLO, "find": find, "replace": 'version = "1.1";'}],
        "commands": [],
        "risks": [],
        "reasoning": "stubbed",
    }


def test_end_to_end_stubbed(repo, monkeypatch):
    stub = StubLLM([plan_json("version = 1.0"), plan_json('version = "1.0";')])
    monkeypatch.setenv("OPENROUTER_BASE_URL", stub.url)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    try:
        from test_workflow import OK, checks, locate_hello

        [outcome] = run(["hello"], repo, BamlClient(), checks(OK), locate_hello)
    finally:
        stub.close()

    assert outcome.status == "updated", outcome
    assert 'version = "1.1";' in (repo / HELLO).read_text()
    assert len(stub.requests) == 2
    assert stub.requests[0]["auth"] == "Bearer test-key"
    assert stub.requests[0]["body"]["model"] == "openai/gpt-6-luna"
    second_prompt = json.dumps(stub.requests[1]["body"]["messages"])
    assert "occurs 0 times" in second_prompt

