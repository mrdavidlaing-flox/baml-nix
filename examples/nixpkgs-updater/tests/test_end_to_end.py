import json

from conftest import HELLO
from fake_claude import FakeClaude
from updater.workflow import BamlClient, run


def plan(find):
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


def test_end_to_end_through_claude_code(repo, tmp_path, monkeypatch):
    from test_workflow import OK, checks, locate_hello

    fake = FakeClaude(tmp_path, monkeypatch, [plan("version = 1.0"), plan('version = "1.0";')])
    [outcome] = run(["hello"], repo, BamlClient(), checks(OK), locate_hello)

    assert outcome.status == "updated", outcome
    assert 'version = "1.1";' in (repo / HELLO).read_text()
    assert len(fake.calls) == 2
    first, second = fake.calls
    # BAML rendered the prompt: the instructions and the inputs.
    assert "You maintain packages in nixpkgs" in first["prompt"]
    assert "Package attribute: hello" in first["prompt"]
    # The first plan's bad edit is fed back into the second prompt.
    assert "occurs 0 times" in second["prompt"]


def test_claude_runs_as_a_plain_model_call(repo, tmp_path, monkeypatch):
    from test_workflow import OK, checks, locate_hello

    fake = FakeClaude(tmp_path, monkeypatch, [plan('version = "1.0";')])
    run(["hello"], repo, BamlClient(model="opus"), checks(OK), locate_hello)

    [call] = fake.calls
    argv = call["argv"]
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[argv.index("--tools") + 1] == ""  # none of Claude Code's own tools
    assert "--no-session-persistence" in argv
    # The output contract travels as a JSON schema, not just prompt text.
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert "needs_update" in json.dumps(schema)
    # Claude starts in an empty temporary directory, not the nixpkgs worktree.
    assert str(repo) not in call["cwd"]
    assert "baml-updater-claude-" in call["cwd"]
