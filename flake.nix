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

        mkWheelPythonPackage =
          {
            pname,
            version,
            url,
            hash,
            propagatedBuildInputs ? [ ],
            pythonImportsCheck ? [ ],
          }:
          pythonPackages.buildPythonPackage {
            inherit
              pname
              version
              propagatedBuildInputs
              pythonImportsCheck
              ;
            format = "wheel";
            src = pkgs.fetchurl {
              inherit
                url
                hash
                ;
            };
            doCheck = false;
          };

        localPythonPackages = rec {
          genai_prices = mkWheelPythonPackage {
            pname = "genai-prices";
            version = "0.0.54";
            url = "https://files.pythonhosted.org/packages/34/71/d2a941b0ca01186912fedb096d8eef7b3e1680c86fdcf8fe3dc84e76d5a9/genai_prices-0.0.54-py3-none-any.whl";
            hash = "sha256-W0UBKymBt9TULEnIYU7pVCD+wkTIdUJUIEV4azb8IjU=";
            propagatedBuildInputs = [
              pythonPackages.httpx
              pythonPackages.pydantic
            ];
            pythonImportsCheck = [ "genai_prices" ];
          };

          griffelib = mkWheelPythonPackage {
            pname = "griffelib";
            version = "2.0.0";
            url = "https://files.pythonhosted.org/packages/4d/51/c936033e16d12b627ea334aaaaf42229c37620d0f15593456ab69ab48161/griffelib-2.0.0-py3-none-any.whl";
            hash = "sha256-AShIeMlmUIttbx2/+bb6YHvAYtgmHFxyU8soWwZCKn8=";
            pythonImportsCheck = [ "griffe" ];
          };

          pydantic_graph = mkWheelPythonPackage {
            pname = "pydantic-graph";
            version = "1.62.0";
            url = "https://files.pythonhosted.org/packages/f0/12/1a9cbcd59fd070ba72b0fe544caa6ca97758518643523ec2bf1162084e0d/pydantic_graph-1.62.0-py3-none-any.whl";
            hash = "sha256-q+Dns1a00yArBp7AINjdH2R/Vemg6FzSctq0glC96H0=";
            propagatedBuildInputs = [
              pythonPackages.httpx
              pythonPackages."logfire-api"
              pythonPackages.pydantic
              pythonPackages."typing-inspection"
            ];
            pythonImportsCheck = [ "pydantic_graph" ];
          };

          pydantic_ai_slim = mkWheelPythonPackage {
            pname = "pydantic-ai-slim";
            version = "1.62.0";
            url = "https://files.pythonhosted.org/packages/3d/67/21e9b3b0944568662e3790c936226bd48a9f27c6b5f27b5916f5857bc4d8/pydantic_ai_slim-1.62.0-py3-none-any.whl";
            hash = "sha256-UhAHP63Ub2WFmmfaZ4RQk8SH8CX6Qw7QJxUfIuxoSrI=";
            propagatedBuildInputs = [
              genai_prices
              griffelib
              pythonPackages.httpx
              pythonPackages."opentelemetry-api"
              pythonPackages.openai
              pydantic_graph
              pythonPackages.pydantic
              pythonPackages.tiktoken
              pythonPackages."typing-inspection"
            ];
            pythonImportsCheck = [ "pydantic_ai" ];
          };

          pydantic_ai = mkWheelPythonPackage {
            pname = "pydantic-ai";
            version = "1.62.0";
            url = "https://files.pythonhosted.org/packages/bc/7a/053aebfab576603e95fcfce1139de4a87e12bd5a2ef1ba00007a931c3ff0/pydantic_ai-1.62.0-py3-none-any.whl";
            hash = "sha256-HriPdFrgReY9pBrWiWboh2yWTQ8CP79daj9dJDNwvQQ=";
            propagatedBuildInputs = [
              pydantic_ai_slim
            ];
            pythonImportsCheck = [ "pydantic_ai" ];
          };
        };

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
            localPythonPackages.pydantic_ai
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
