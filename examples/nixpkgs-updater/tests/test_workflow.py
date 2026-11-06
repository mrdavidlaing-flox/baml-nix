from pathlib import Path

import baml_sdk
from conftest import HELLO, PACKAGE_NIX
from updater.tools import Tools
from updater.workflow import Outcome, run

OK = baml_sdk.CommandResult(exit_code=0, output="built")


def a_plan(needs_update=True, edits=None, version="1.1") -> baml_sdk.UpdatePlan:
    if edits is None:
        edits = [baml_sdk.Edit(path=HELLO, find='version = "1.0";', replace=f'version = "{version}";')]
    return baml_sdk.UpdatePlan(
        attr="hello",
        current_version="1.0",
        target_version=version,
        needs_update=needs_update,
        edits=edits,
        commands=[],
        risks=[],
        reasoning="test",
    )


class FakeClient:
    """Stands in for the LLM-backed PlanUpdate; ApplyUpdate is the real one."""

    def __init__(self, repo: Path, plans):
        self.repo = repo
        self.plans = list(plans)
        self.calls = []
        self.applied = 0

    def plan_update(self, attr, current_version, package_nix, package_path, previous_errors):
        self.calls.append(dict(attr=attr, package_nix=package_nix, previous_errors=list(previous_errors)))
        return self.plans.pop(0) if len(self.plans) > 1 else self.plans[0]

    def apply_update(self, plan, tools: Tools):
        self.applied += 1
        return baml_sdk.apply_update_sync(plan, tools.read_file, tools.write_file, tools.run_command)


def locate_hello(attr):
    if attr != "hello":
        raise LookupError(f"attribute '{attr}' not found")
    return HELLO, "1.0"


def checks(*results):
    results = list(results)
    calls = []

    def check(attr):
        calls.append(attr)
        return results.pop(0) if len(results) > 1 else results[0]

    check.calls = calls
    return check


def failed(output):
    return baml_sdk.CommandResult(exit_code=1, output=output)


def test_success_first_try(repo):
    client = FakeClient(repo, [a_plan()])
    [outcome] = run(["hello"], repo, client, checks(OK), locate_hello)
    assert outcome == Outcome("hello", "1.0", "1.1", "updated", outcome.detail)
    assert 'version = "1.1";' in (repo / HELLO).read_text()


def test_retry_feeds_errors_back(repo):
    client = FakeClient(repo, [a_plan(), a_plan()])
    check = checks(failed("hash mismatch\n got: sha256-REAL="), OK)
    [outcome] = run(["hello"], repo, client, check, locate_hello)
    assert outcome.status == "updated"
    assert client.calls[0]["previous_errors"] == []
    assert any("sha256-REAL=" in e for e in client.calls[1]["previous_errors"])


def test_apply_failure_feeds_errors_back_without_check(repo):
    bad = a_plan(edits=[baml_sdk.Edit(path=HELLO, find="nope", replace="x")])
    client = FakeClient(repo, [bad, a_plan()])
    check = checks(OK)
    [outcome] = run(["hello"], repo, client, check, locate_hello)
    assert outcome.status == "updated"
    assert check.calls == ["hello"]
    assert any("occurs 0 times" in e for e in client.calls[1]["previous_errors"])


def test_gives_up_after_3(repo):
    client = FakeClient(repo, [a_plan()])
    [outcome] = run(["hello"], repo, client, checks(failed("still broken")), locate_hello)
    assert outcome.status == "failed"
    assert len(client.calls) == 3
    assert "still broken" in outcome.detail
    assert (repo / HELLO).read_text() == PACKAGE_NIX


def test_already_current(repo):
    client = FakeClient(repo, [a_plan(needs_update=False, edits=[], version="1.0")])
    check = checks(OK)
    [outcome] = run(["hello"], repo, client, check, locate_hello)
    assert outcome.status == "current"
    assert client.applied == 0
    assert check.calls == []


def test_retry_starts_from_clean_tree(repo):
    client = FakeClient(repo, [a_plan(), a_plan()])
    run(["hello"], repo, client, checks(failed("nope"), OK), locate_hello)
    assert client.calls[1]["package_nix"] == PACKAGE_NIX


def test_unknown_attr_reported_and_loop_continues(repo):
    client = FakeClient(repo, [a_plan()])
    outcomes = run(["nope", "hello"], repo, client, checks(OK), locate_hello)
    assert [(o.attr, o.status) for o in outcomes] == [("nope", "failed"), ("hello", "updated")]
    assert "not found" in outcomes[0].detail


def test_missing_api_key_fails_before_worktree(monkeypatch, capsys):
    from updater import __main__ as cli
    from updater import workflow

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    created = []
    monkeypatch.setattr(workflow, "create_worktree", lambda *a: created.append(a))
    assert cli.main(["hello"]) == 2
    assert capsys.readouterr().err.strip() == "error: OPENROUTER_API_KEY is not set"
    assert created == []


def test_failed_package_does_not_undo_earlier_success(repo):
    import subprocess

    shared = "pkgs/top-level/versions.nix"
    (repo / "pkgs/top-level").mkdir(parents=True)
    (repo / shared).write_text('{ hello = "1.0"; world = "2.0"; }\n')
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "shared"], check=True)

    def edit(find, replace):
        return baml_sdk.Edit(path=shared, find=find, replace=replace)

    hello_plan = a_plan(edits=[edit('hello = "1.0"', 'hello = "1.1"')])
    world_plan = a_plan(edits=[edit('world = "2.0"', 'world = "2.1"'), baml_sdk.Edit(path="pkgs/new.nix", find="", replace="x")])

    class TwoPackages(FakeClient):
        def plan_update(self, attr, current_version, package_nix, package_path, previous_errors):
            self.calls.append(dict(attr=attr, package_nix=package_nix, previous_errors=list(previous_errors)))
            return hello_plan if attr == "hello" else world_plan

        def apply_update(self, plan, tools):
            result = super().apply_update(plan, tools)
            if plan is world_plan:
                tools.write_file("pkgs/new.nix", "created by a failed attempt")
            return result

    def locate(attr):
        return shared, "1.0"

    def check(attr):
        return OK if attr == "hello" else failed("world does not build")

    outcomes = run(["hello", "world"], repo, TwoPackages(repo, []), check, locate)
    assert [(o.attr, o.status) for o in outcomes] == [("hello", "updated"), ("world", "failed")]
    assert (repo / shared).read_text() == '{ hello = "1.1"; world = "2.0"; }\n'
    assert not (repo / "pkgs/new.nix").exists()
