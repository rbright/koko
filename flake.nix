{
  description = "koko: local Kokoro-82M CLI text-to-speech";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in
    (flake-utils.lib.eachSystem supportedSystems (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonPackages = pkgs.python313Packages;
        runtimeTools = [
          pkgs.ffmpeg
          pkgs.alsa-utils
          pkgs.espeak-ng
        ];

        kokoPackage = pythonPackages.buildPythonApplication {
          pname = "koko";
          version = "0.1.0";
          src = self;
          format = "pyproject";

          nativeBuildInputs = [
            pythonPackages.hatchling
            pkgs.makeWrapper
          ];

          propagatedBuildInputs = [
            pythonPackages.kokoro
            pythonPackages.pydantic-settings
          ];

          pythonImportsCheck = [
            "koko_cli"
          ];

          postFixup = ''
            wrapProgram "$out/bin/koko" \
              --prefix PATH : "${pkgs.lib.makeBinPath runtimeTools}"
          '';
        };
      in
      {
        packages = {
          koko = kokoPackage;
          default = kokoPackage;
        };

        apps = {
          koko = {
            type = "app";
            program = "${kokoPackage}/bin/koko";
          };
          default = {
            type = "app";
            program = "${kokoPackage}/bin/koko";
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python313
            pkgs.uv
            pkgs.just
            pkgs.ruff
            pkgs.ty
            pythonPackages.pytest
            pkgs.prek
            pkgs.ffmpeg
            pkgs.alsa-utils
            pkgs.espeak-ng
            pkgs.deadnix
            pkgs.statix
            pkgs.nixfmt
            pkgs.ripgrep
          ];
        };

        formatter = pkgs.nixfmt;
      }
    ))
    // {
      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          cfg = config.programs.koko;
        in
        {
          options.programs.koko.enable = lib.mkEnableOption "koko Kokoro-82M CLI";

          config = lib.mkIf cfg.enable {
            environment.systemPackages = [ self.packages.${pkgs.system}.koko ];
          };
        };
    };
}
