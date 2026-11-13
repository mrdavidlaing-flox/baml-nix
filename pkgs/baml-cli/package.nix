{
  lib,
  rustPlatform,
  fetchFromGitHub,
  pkg-config,
  makeBinaryWrapper,
  aws-lc,
  sqlite,
  versionCheckHook,
  nix-update-script,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "baml-cli";
  version = "0.25.2";

  src = fetchFromGitHub {
    owner = "BoundaryML";
    repo = "baml";
    tag = "baml-language-${finalAttrs.version}";
    hash = "sha256-bHh4+usYxLDijJqR9ONp9lULX7kBloNvgRApKPPdP/A=";
  };

  cargoRoot = "baml_language";
  buildAndTestSubdir = "baml_language";

  cargoHash = "sha256-HQR+MWlJhCPLTvvB7vND2icQyW2VEG47RxtSmA6Jmrk=";

  cargoBuildFlags = [
    "--bin"
    "baml-cli"
    "--bin"
    "baml-pack-host"
  ];

  # nixpkgs' cargoSetupHook makes aws-lc-sys (via rustls) and libsqlite3-sys
  # link system libraries, found via pkg-config, instead of bundled copies.
  nativeBuildInputs = [
    pkg-config
    makeBinaryWrapper
  ];
  buildInputs = [
    aws-lc
    sqlite
  ];

  # The source tarball has no .git; baml_artifact's build script needs the
  # commit being built. Must be the commit of the tag above.
  env.BAML_GIT_SHA = "08e3d200287ab83244024b191e32fdad48f006d1";

  # baml_cli's suite is large and mostly end-to-end (network, telemetry,
  # agent installs). Behaviour is covered by versionCheckHook and the
  # baml and python3Packages.baml-bridge passthru tests.
  doCheck = false;

  # baml-cli sends anonymous usage analytics to PostHog by default. Turn them
  # off, as gh and glab do: DO_NOT_TRACK is upstream's only opt-out variable.
  # --set-default keeps the user's choice: DO_NOT_TRACK=0 opts back in.
  # `baml` runs this wrapper, so it is covered too.
  postInstall = ''
    wrapProgram $out/bin/baml-cli --set-default DO_NOT_TRACK 1
  '';

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
