{
  lib,
  rustPlatform,
  fetchFromGitHub,
  versionCheckHook,
  nix-update-script,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "baml-cli";
  version = "0.24.0";

  src = fetchFromGitHub {
    owner = "BoundaryML";
    repo = "baml";
    tag = "baml-language-${finalAttrs.version}";
    hash = "sha256-75hAD4akeaJmOEjjzIjskIQVPHgiBT//shlriX+2y/Q=";
  };

  cargoRoot = "baml_language";
  buildAndTestSubdir = "baml_language";

  cargoHash = "sha256-BAIWoqJdOwkA/Oc5SCrZRJAr1ku14t2Rr2mJP95JXAs=";

  cargoBuildFlags = [
    "--bin"
    "baml-cli"
    "--bin"
    "baml-pack-host"
  ];

  # The source tarball has no .git; baml_artifact's build script needs the
  # commit being built. Must be the commit of the tag above.
  env.BAML_GIT_SHA = "dec4713a0e7c9699442bf5855b4f327063f769c5";

  # baml_cli's suite is large and mostly end-to-end (network, telemetry,
  # agent installs). Behaviour is covered by versionCheckHook and the
  # baml and python3Packages.baml-bridge passthru tests.
  doCheck = false;

  nativeInstallCheckInputs = [ versionCheckHook ];
  doInstallCheck = true;

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "^baml-language-([0-9]+\\.[0-9]+\\.[0-9]+)$"
    ];
  };

  meta = {
    description = "Toolchain for BAML, a programming language for building agents";
    homepage = "https://github.com/BoundaryML/baml";
    license = lib.licenses.asl20;
    maintainers = [ ];
    mainProgram = "baml-cli";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
})
