import pytest
from fake_claude import FakeClaude
from updater import claude

PLAN = {
    "attr": "hello",
    "current_version": "1.0",
    "target_version": "1.0",
    "needs_update": False,
    "edits": [],
    "commands": [],
    "risks": [],
    "reasoning": "already current",
}


def plan(**kw):
    return claude.plan_update("hello", "1.0", "{ }", "pkgs/hello/package.nix", [], **kw)


def test_structured_output_becomes_an_update_plan(tmp_path, monkeypatch):
    FakeClaude(tmp_path, monkeypatch, [PLAN])
    result = plan()
    assert result.needs_update is False
    assert result.reasoning == "already current"


def test_default_model_is_sonnet(tmp_path, monkeypatch):
    fake = FakeClaude(tmp_path, monkeypatch, [PLAN])
    plan()
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("--model") + 1] == "sonnet"


def test_cli_crash_raises(tmp_path, monkeypatch):
    # BAML reads the event stream before the exit code, so a CLI that dies
    # without output is reported as a missing result.
    FakeClaude(tmp_path, monkeypatch, [PLAN], exit_code=3)
    with pytest.raises(Exception, match="without a result event"):
        plan()


def test_reported_error_raises(tmp_path, monkeypatch):
    FakeClaude(tmp_path, monkeypatch, ["usage limit reached"], is_error=True)
    with pytest.raises(Exception, match="usage limit reached"):
        plan()


def test_preflight(tmp_path, monkeypatch):
    FakeClaude(tmp_path, monkeypatch, [PLAN])
    assert claude.preflight() is None


def test_preflight_logged_out(tmp_path, monkeypatch):
    FakeClaude(tmp_path, monkeypatch, [PLAN], logged_in=False)
    assert "not logged in" in claude.preflight()


def test_preflight_missing_binary(monkeypatch):
    monkeypatch.setenv("CLAUDE_BIN", "definitely-not-claude")
    assert "not found on PATH" in claude.preflight()
