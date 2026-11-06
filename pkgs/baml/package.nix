{
  lib,
  stdenvNoCC,
  replaceVars,
  coreutils,
  gnugrep,
  gnused,
  baml-cli,
  callPackage,
}:

# The `baml` command for Nix. Upstream's launcher selects and downloads
# toolchains; here the toolchain is baml-cli from the same release, and a
# project asking for any other version is refused (see baml.sh).
stdenvNoCC.mkDerivation {
  pname = "baml";
  inherit (baml-cli) version;

  dontUnpack = true;

  installPhase = ''
    runHook preInstall
    install -Dm755 ${
      replaceVars ./baml.sh {
        inherit (baml-cli) version;
        cli = "${baml-cli}/bin/baml-cli";
        sed = lib.getExe gnused;
        grep = lib.getExe gnugrep;
        dirname = "${coreutils}/bin/dirname";
      }
    } $out/bin/baml
    runHook postInstall
  '';

  passthru.tests.policy = callPackage ./tests/policy.nix { };

  meta = {
    description = "BAML, a programming language for building agents";
    homepage = "https://github.com/BoundaryML/baml";
    license = lib.licenses.asl20;
    maintainers = [ ];
    mainProgram = "baml";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
}
