{
  lib,
  stdenv,
  rustPlatform,
  fetchFromGitHub,
  libiconv,
  versionCheckHook,
  nix-update-script,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "baml-cli";
  version = "0.226.3";

  src = fetchFromGitHub {
    owner = "BoundaryML";
    repo = "baml";
    tag = "v${finalAttrs.version}";
    hash = "sha256-29Tibj5OR0O/WhN4hlVcFhBxRGqWTg/el5/4HkGV0ds=";
  };

  cargoRoot = "engine";
  buildAndTestSubdir = "engine";

  cargoHash = "sha256-A789ezj2r9BpmZCUBZa8Ht1UO68wgK1oiMcfsJYhK0k=";

  cargoBuildFlags = [
    "-p"
    "baml-cli"
  ];

  # Upstream sets this in engine/.cargo/config.toml; set it explicitly so it
  # survives any RUSTFLAGS from the environment.
  env.RUSTFLAGS = "--cfg tracing_unstable";

  buildInputs = lib.optionals stdenv.hostPlatform.isDarwin [ libiconv ];

  # The baml-cli crate itself has no tests; behaviour is covered by
  # versionCheckHook here and python3Packages.baml-py.tests.generate.
  doCheck = false;

  nativeInstallCheckInputs = [ versionCheckHook ];
  doInstallCheck = true;

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI for BAML, a language for building reliable AI workflows and agents";
    homepage = "https://github.com/BoundaryML/baml";
    changelog = "https://github.com/BoundaryML/baml/blob/v${finalAttrs.version}/CHANGELOG.md";
    license = lib.licenses.asl20;
    maintainers = [ ];
    mainProgram = "baml-cli";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
})
