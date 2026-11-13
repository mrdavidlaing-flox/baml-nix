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


DANGEROUS = [
    # git: write outside, read anything, run diff drivers
    ["git", "diff", "--output=/tmp/x", "HEAD"],
    ["git", "diff", "--output", "/tmp/x"],
    ["git", "diff", "--no-index", "/dev/null", "/etc/passwd"],
    ["git", "diff", "--ext-diff"],
    ["git", "diff", "--", "../outside.txt"],
    ["git", "status", "--untracked-files=all", "--ignored", "-z", "--porcelain", "x"],
    # nix-update: run code, commit, write elsewhere
    ["nix-update", "--use-update-script", "hello"],
    ["nix-update", "-u", "hello"],
    ["nix-update", "--run", "sh", "hello"],
    ["nix-update", "--shell", "hello"],
    ["nix-update", "--commit", "hello"],
    ["nix-update", "--override-filename", "/etc/x", "hello"],
    ["nix-update", "hello", "other"],
    # nix build: arbitrary expressions, impurity, links outside, unsafe options
    ["nix", "build", "--expr", "1"],
    ["nix", "build", "--impure", "--file", ".", "hello"],
    ["nix", "build", "--out-link", "/tmp/x", "--file", ".", "hello"],
    ["nix", "build", "--option", "allow-unsafe-native-code-during-evaluation", "true", "--file", ".", "hello"],
    ["nix", "build", "--file", "/etc", "hello"],
    ["nix", "build", ".#hello"],
    ["nix", "build", "--file", ".", "--", "-x"],
    # prefetchers: local files, non-https, unknown flags
    ["nix-prefetch-url", "file:///etc/passwd"],
    ["nix-prefetch-url", "http://example.invalid/x.tar.gz"],
    ["nix-prefetch-url", "--name", "x", "https://example.invalid/x.tar.gz"],
    ["nix-prefetch-git", "file:///home"],
    ["nix-prefetch-git", "--builder", "https://example.invalid/x.git"],
]

SAFE = [
    ["nix", "build", "--file", ".", "hello"],
    ["nix", "build", "--no-link", "-L", "--file", ".", "python3Packages.requests"],
    ["nix-update", "hello"],
    ["nix-update", "--version=1.2.3", "hello"],
    ["nix-update", "--version", "1.2.3", "hello"],
    ["nix-prefetch-url", "https://example.invalid/x.tar.gz"],
    ["nix-prefetch-url", "--unpack", "https://example.invalid/x.tar.gz"],
    ["nix-prefetch-git", "https://example.invalid/x.git", "v1.2.3"],
    ["nix-prefetch-git", "--rev", "v1.2.3", "--fetch-submodules", "https://example.invalid/x.git"],
    ["git", "diff"],
    ["git", "diff", "--stat"],
    ["git", "diff", "--", HELLO],
    ["git", "status", "--short"],
]


def test_allowlist_rejects_dangerous_shapes(repo: Path):
    tools = Tools(repo)
    for argv in DANGEROUS:
        assert tools.refusal(argv) is not None, argv
        assert tools.run_command(argv).exit_code == 126, argv


def test_allowlist_accepts_safe_shapes(repo: Path):
    tools = Tools(repo)
    for argv in SAFE:
        assert tools.refusal(argv) is None, argv


def test_git_diff_output_flag_cannot_write(repo: Path, tmp_path: Path):
    target = tmp_path / "clobbered"
    Tools(repo).run_command(["git", "diff", f"--output={target}", "HEAD"])
    assert not target.exists()


def test_git_internals_refused(repo: Path):
    tools = Tools(repo)
    for path in [".git", ".git/config", "pkgs/../.git/HEAD"]:
        with pytest.raises(ToolRefused):
            tools.write_file(path, "x")


def test_nix_env_enables_nix_command_and_keeps_user_config():
    from updater.tools import nix_env

    assert nix_env({})["NIX_CONFIG"] == "extra-experimental-features = nix-command"
    env = nix_env({"NIX_CONFIG": "max-jobs = 4", "HOME": "/h"})
    assert env["NIX_CONFIG"] == "max-jobs = 4\nextra-experimental-features = nix-command"
    assert env["HOME"] == "/h"


def test_commands_run_with_nix_command_enabled(repo, monkeypatch):
    import subprocess

    seen = {}
    real_run = subprocess.run

    def spy(argv, **kw):
        seen["env"] = kw.get("env")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", spy)
    monkeypatch.delenv("NIX_CONFIG", raising=False)
    Tools(repo).run_command(["git", "status", "--short"])
    assert "nix-command" in seen["env"]["NIX_CONFIG"]
