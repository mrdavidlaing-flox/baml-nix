# baml-py's extension is built with pyo3's abi3-py38, so the one build should
# import under other CPython 3 versions too. Point older and newer
# interpreters straight at this build's site-packages. (The Python package
# scope forbids python3XX arguments, hence pkgs.)
{
  lib,
  runCommand,
  pkgs,
  python,
  baml-py,
}:

runCommand "baml-py-abi3-test" { } ''
  export PYTHONPATH=${baml-py}/${python.sitePackages}
  ${lib.concatMapStringsSep "\n"
    (py: ''
      echo "importing baml_py with ${py.name}"
      ${py.interpreter} -c "import baml_py; print(baml_py.__file__)"
    '')
    [
      pkgs.python313
      pkgs.python314
    ]
  }
  touch $out
''
