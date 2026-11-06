{
  description = "The BAML language (baml, baml-cli, python3Packages.baml-bridge) packaged nixpkgs-style";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        # nixpkgs unstable dropped x86_64-darwin in 26.11.
        "aarch64-darwin"
      ];
      forAllSystems =
        f:
        nixpkgs.lib.genAttrs systems (
          system:
          f (
            import nixpkgs {
              inherit system;
              overlays = [ self.overlays.default ];
            }
          )
        );
    in
    {
      # Package files are plain callPackage functions so they can be copied
      # into nixpkgs unchanged.
      overlays.default = final: prev: {
        baml-cli = final.callPackage ./pkgs/baml-cli/package.nix { };
      };

      packages = forAllSystems (pkgs: {
        inherit (pkgs) baml-cli;
      });

      checks = forAllSystems (pkgs: {
        baml-cli-version = pkgs.callPackage ./pkgs/baml-cli/tests/version.nix { };
      });
    };
}
