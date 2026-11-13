{
  lib,
  buildPythonPackage,
  callPackage,
  rustPlatform,
  pkg-config,
  aws-lc,
  baml-cli,
  protobuf,
  pydantic,
  typing-extensions,
}:

buildPythonPackage {
  pname = "baml-bridge";
  # Same source tree and Cargo workspace as baml-cli, so they bump together.
  inherit (baml-cli) version src cargoDeps;
  pyproject = true;

  sourceRoot = "${baml-cli.src.name}/baml_language";
  # maturin reads manifest-path (rust/bridge_python) from this pyproject.toml.
  buildAndTestSubdir = "sdks/python";

  nativeBuildInputs = [
    rustPlatform.cargoSetupHook
    rustPlatform.maturinBuildHook
    pkg-config
  ];

  # System AWS-LC for aws-lc-sys (via rustls), as for baml-cli. Unlike
  # baml-cli, the bridge doesn't use libsqlite3-sys.
  buildInputs = [ aws-lc ];

  env.BAML_GIT_SHA = baml-cli.BAML_GIT_SHA;

  dependencies = [
    protobuf
    pydantic
    typing-extensions
  ];

  pythonImportsCheck = [ "baml_bridge" ];

  passthru.tests.generate = callPackage ./tests/generate.nix { };

  meta = {
    description = "Python runtime for SDKs generated from BAML";
    homepage = "https://github.com/BoundaryML/baml";
    license = lib.licenses.asl20;
    maintainers = [ ];
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
}
