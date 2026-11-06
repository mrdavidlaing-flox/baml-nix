{
  description = "BAML v0 (baml-cli, python3Packages.baml-py) packaged nixpkgs-style";

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
        pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
          (pyFinal: pyPrev: {
            baml-py = pyFinal.callPackage ./pkgs/python-modules/baml-py { };
          })
        ];
      };

      packages = forAllSystems (pkgs: {
        inherit (pkgs) baml-cli;
        inherit (pkgs.python3Packages) baml-py;
        default = pkgs.baml-cli;
      });

      checks = forAllSystems (pkgs: {
        baml-cli-version = pkgs.callPackage ./pkgs/baml-cli/tests/version.nix { };
        baml-py-generate = pkgs.python3Packages.baml-py.tests.generate;
        baml-py-abi3 = pkgs.python3Packages.baml-py.tests.abi3;
      });
    };
}
