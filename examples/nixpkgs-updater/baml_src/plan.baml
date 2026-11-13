// One text replacement in a file, relative to the nixpkgs worktree.
// `find` must occur exactly once in the file.
class Edit {
  path string
  find string
  replace string
}

class UpdatePlan {
  attr string
  current_version string
  target_version string
  needs_update bool
  edits Edit[]
  // Commands to run after the edits, each as an argv list.
  commands string[][]
  risks string[]
  reasoning string
}

// Works out how to bump one nixpkgs package to its latest upstream release.
function PlanUpdate(
  attr: string,
  current_version: string,
  package_nix: string,
  package_path: string,
  previous_errors: string[],
) -> UpdatePlan {
  client: ClaudeCode
  prompt: `
    ${role("system")}
    You maintain packages in nixpkgs. Plan how to update one package to its
    latest stable upstream release. Your plan is executed by a program, not
    a person, so it must be exact:

    - Each edit replaces one exact piece of text in a file. The "find" text
      must occur exactly once in that file; copy it character for character,
      including indentation. Prefer whole lines.
    - To get a new hash, set it to lib.fakeHash in an edit; the build error
      reports the real hash and you will see it in previous_errors.
    - Commands must have exactly one of these shapes; anything else (any
      other flag) is refused. Leave commands empty if the edits are enough.
        nix build [--no-link] [-L] --file . ATTR
        nix-update [--version=V] ATTR
        nix-prefetch-url [--unpack] https://URL
        nix-prefetch-git [--rev REV] [--fetch-submodules] https://URL [REV]
        git diff [--stat] [-- PATH...]
        git status [--short]
    - If the package is already at the latest release, set needs_update to
      false and leave edits and commands empty.
    - Note anything risky (tag naming traps, prereleases, major-version
      breakage) in risks.

    ${role("user")}
    Package attribute: ${attr}
    Current version: ${current_version}
    File: ${package_path}

    ${package_nix}

    Errors from previous attempts (most recent last):
    ${previous_errors.join("\n---\n")}

    ${ctx.output_format()}
  `
}
