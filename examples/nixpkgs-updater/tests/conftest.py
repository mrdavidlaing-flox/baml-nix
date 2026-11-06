import os
import subprocess
from pathlib import Path

import pytest

PACKAGE_NIX = """{ lib, stdenv, fetchurl }:

stdenv.mkDerivation (finalAttrs: {
  pname = "hello";
  version = "1.0";

  src = fetchurl {
    url = "https://example.invalid/hello-${finalAttrs.version}.tar.gz";
    hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  };

  meta.description = "Says hello (release 1.0)";
})
"""

os.environ.setdefault("GIT_AUTHOR_NAME", "test")
os.environ.setdefault("GIT_AUTHOR_EMAIL", "test@example.invalid")
os.environ.setdefault("GIT_COMMITTER_NAME", "test")
os.environ.setdefault("GIT_COMMITTER_EMAIL", "test@example.invalid")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tiny git repo shaped like nixpkgs, with one package."""
    root = tmp_path / "nixpkgs"
    (root / "pkgs" / "hello").mkdir(parents=True)
    (root / "pkgs" / "hello" / "package.nix").write_text(PACKAGE_NIX)
    subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "init"], check=True)
    return root


HELLO = "pkgs/hello/package.nix"
