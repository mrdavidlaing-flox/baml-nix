{
  lib,
  stdenv,
  buildPythonPackage,
  callPackage,
  rustPlatform,
  libiconv,
  baml-cli,
}:

buildPythonPackage {
  pname = "baml-py";
  # Same source tree and Cargo workspace as baml-cli, so the two bump together.
  inherit (baml-cli) version src cargoDeps;
  pyproject = true;

  sourceRoot = "${baml-cli.src.name}/engine";
  buildAndTestSubdir = "language_client_python";

  nativeBuildInputs = [
    rustPlatform.cargoSetupHook
    rustPlatform.maturinBuildHook
  ];

  buildInputs = lib.optionals stdenv.hostPlatform.isDarwin [ libiconv ];

  env.RUSTFLAGS = "--cfg tracing_unstable";

  # The generated baml_client needs pydantic, but baml_py itself does not:
  # upstream deliberately declares no runtime dependencies.
  dependencies = [ ];

  pythonImportsCheck = [ "baml_py" ];

  passthru.tests = {
    generate = callPackage ./tests/generate.nix { };
    abi3 = callPackage ./tests/abi3.nix { };
  };

  meta = {
    description = "Python runtime for BAML-generated clients, including baml-cli";
    homepage = "https://github.com/BoundaryML/baml";
    changelog = "https://github.com/BoundaryML/baml/blob/v${baml-cli.version}/CHANGELOG.md";
    license = lib.licenses.asl20;
    maintainers = [ ];
    mainProgram = "baml-cli";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
}
