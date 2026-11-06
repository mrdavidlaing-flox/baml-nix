class CommandResult {
  exit_code int
  output string
}

class ApplyResult {
  ok bool
  steps_done string[]
  failed_step string?
  failed_output string?
}

// Carries out a plan exactly: no LLM here. Edits first, then commands; the
// first failing step stops it. The callbacks are Python functions jailed to
// the nixpkgs worktree (updater/tools.py).
function ApplyUpdate(
  plan: UpdatePlan,
  read_file: (string) -> string throws baml.errors.HostCallable,
  write_file: (string, string) -> void throws baml.errors.HostCallable,
  run_command: (string[]) -> CommandResult throws baml.errors.HostCallable,
) -> ApplyResult {
  let done: string[] = [];
  for (let edit in plan.edits) {
    let step = "edit " + edit.path;
    let content = read_file(edit.path) catch (e) {
      _ => {
        return ApplyResult { ok: false, steps_done: done, failed_step: step, failed_output: e.message };
      }
    };
    let occurrences = content.split(edit.find).length() - 1;
    if (occurrences != 1) {
      return ApplyResult {
        ok: false,
        steps_done: done,
        failed_step: step,
        failed_output: "find text occurs " + occurrences.to_string() + " times in " + edit.path + "; it must occur exactly once",
      };
    }
    write_file(edit.path, content.replace(edit.find, edit.replace)) catch (e) {
      _ => {
        return ApplyResult { ok: false, steps_done: done, failed_step: step, failed_output: e.message };
      }
    };
    done.push(step);
  }
  for (let argv in plan.commands) {
    let step = "run " + argv.join(" ");
    let result = run_command(argv) catch (e) {
      _ => {
        return ApplyResult { ok: false, steps_done: done, failed_step: step, failed_output: e.message };
      }
    };
    if (result.exit_code != 0) {
      return ApplyResult { ok: false, steps_done: done, failed_step: step, failed_output: result.output };
    }
    done.push(step);
  }
  ApplyResult { ok: true, steps_done: done, failed_step: null, failed_output: null }
}
