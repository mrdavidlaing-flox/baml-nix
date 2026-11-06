import os
from pathlib import Path

import pytest

import baml_sdk
from conftest import HELLO, PACKAGE_NIX
from updater.tools import ToolRefused, Tools


def test_paths_outside_worktree_refused(repo: Path, tmp_path: Path):
    tools = Tools(repo)
    (tmp_path / "outside.txt").write_text("secret")
    os.symlink(tmp_path, repo / "escape")
    for path in ["../outside.txt", "/etc/passwd", "escape/outside.txt"]:
        with pytest.raises(ToolRefused):
            tools.read_file(path)
        with pytest.raises(ToolRefused):
            tools.write_file(path, "x")
    assert (tmp_path / "outside.txt").read_text() == "secret"


def test_reads_and_writes_inside_worktree(repo: Path):
    tools = Tools(repo)
    assert tools.read_file(HELLO) == PACKAGE_NIX
    tools.write_file(HELLO, "changed")
    assert (repo / HELLO).read_text() == "changed"


def test_allowlist(repo: Path):
    tools = Tools(repo)
    assert tools.run_command(["git", "status"]).exit_code == 0
    for argv in [["sh", "-c", "touch pwned"], ["nix", "eval", "--expr", "1"], ["git", "push"], [], ["nix"]]:
        result = tools.run_command(argv)
        assert result.exit_code == 126, argv
        assert "not allowed" in result.output
    assert not (repo / "pwned").exists()


def plan(**overrides) -> baml_sdk.UpdatePlan:
    fields = dict(
        attr="hello",
        current_version="1.0",
        target_version="1.1",
        needs_update=True,
        edits=[],
        commands=[],
        risks=[],
        reasoning="test",
    )
    fields.update(overrides)
    return baml_sdk.UpdatePlan(**fields)


def apply(repo: Path, p: baml_sdk.UpdatePlan) -> baml_sdk.ApplyResult:
    tools = Tools(repo)
    return baml_sdk.apply_update_sync(p, tools.read_file, tools.write_file, tools.run_command)


def test_apply_edits_and_runs_commands(repo: Path):
    edit = baml_sdk.Edit(path=HELLO, find='version = "1.0";', replace='version = "1.1";')
    result = apply(repo, plan(edits=[edit], commands=[["git", "diff", "--stat"]]))
    assert result.ok, result
    assert result.steps_done == [f"edit {HELLO}", "run git diff --stat"]
    assert 'version = "1.1";' in (repo / HELLO).read_text()


def test_edit_find_must_match_exactly_once(repo: Path):
    for find, count in [("no such text", 0), ("1.0", 2)]:
        edit = baml_sdk.Edit(path=HELLO, find=find, replace="X")
        result = apply(repo, plan(edits=[edit]))
        assert not result.ok
        assert result.failed_step == f"edit {HELLO}"
        assert f"occurs {count} times" in result.failed_output
        assert (repo / HELLO).read_text() == PACKAGE_NIX


def test_refused_path_fails_the_step(repo: Path):
    edit = baml_sdk.Edit(path="../../etc/passwd", find="root", replace="x")
    result = apply(repo, plan(edits=[edit]))
    assert not result.ok
    assert result.failed_step == "edit ../../etc/passwd"
    assert "outside the worktree" in result.failed_output


def test_failing_or_refused_command_stops(repo: Path):
    edit = baml_sdk.Edit(path=HELLO, find='version = "1.0";', replace='version = "1.1";')
    result = apply(repo, plan(edits=[edit], commands=[["sh", "-c", "echo hi"], ["git", "status"]]))
    assert not result.ok
    assert result.steps_done == [f"edit {HELLO}"]
    assert result.failed_step == "run sh -c echo hi"
    assert "not allowed" in result.failed_output
