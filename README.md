# koko

Local CLI text-to-speech using [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) for on-demand inference.

- No daemon/background service.
- Run directly as `koko`.
- Default voice: `af_heart`.
- Designed for automation workflows (including agent-completion voice notifications).

## Features

- `koko "Your message"` default speak flow (sag-style UX)
- `-v/--voice` flag to pick a voice (`af_heart` by default)
- `koko voices` and `koko -v ?` voice discovery
- Message input from args, file, or stdin
- WAV output via `--output`
- Optional playback toggle via `--play/--no-play`

## Requirements

- Python `3.13.11`
- A local audio player for playback (auto-detected):
  - Linux: `ffplay`, `aplay`, or `paplay`
  - macOS: `afplay`

`koko` is configured for **local-only execution by default**. It will not make network requests unless you explicitly pass `--no-offline`.

## Quickstart (development)

```bash
uv sync --dev
export KOKO_MODEL_DIR=/path/to/kokoro-82m
uv run koko "Hello from koko"
```

## CLI Usage

```bash
koko [flags] [message...]
```

### Common examples

```bash
# Default voice (af_heart)
koko "Agent task finished successfully."

# Explicit voice
koko --voice bf_emma "Build complete."

# Save output to WAV (no playback)
koko --no-play --output /tmp/done.wav "Pipeline completed."

# Read text from stdin
echo "Deployment completed." | koko

# Read text from file
koko --input-file ./message.txt

# List voices
koko voices
koko -v ?
```

## Local model setup (required by default)

`koko` runs in offline mode by default. Place model assets on disk and point `koko` to them.

Download model assets (one-time):

```bash
just download-model
```

Or download only specific voices:

```bash
just download-model voices="af_heart,bf_emma"
```

Expected local model layout:

```text
/path/to/kokoro-82m/
  config.json
  kokoro-v1_0.pth
  voices/
    af_heart.pt
    ...
```

Use it directly:

```bash
koko --model-dir /path/to/kokoro-82m --voice af_heart "Task complete"
```

You can also set a default path via environment variable:

```bash
export KOKO_MODEL_DIR=/path/to/kokoro-82m
koko "Task complete"
```

`koko` fails fast if required local assets are missing.

### Key flags

- `-v, --voice` — voice ID (default: `af_heart`)
- `-l, --lang-code` — explicit language code (`a,b,e,f,h,i,j,p,z`)
- `-s, --speed` — speech speed multiplier (`> 0`)
- `-o, --output` — write WAV output file
- `-f, --input-file` — input text file (`-` for stdin)
- `--device` — `auto` (default), `cpu`, or `cuda`
- `--play/--no-play` — enable or disable local playback
- `--repo-id` — Hugging Face model repo (default: `hexgrad/Kokoro-82M`)
- `--model-dir` — local model asset directory (`config.json`, `kokoro-v1_0.pth`, `voices/*.pt`)
- `--offline/--no-offline` — local-only mode toggle (default: `--offline`)

### Environment defaults (via pydantic-settings)

You can set defaults with `KOKO_*` environment variables:

- `KOKO_REPO_ID`
- `KOKO_DEFAULT_VOICE`
- `KOKO_OFFLINE`
- `KOKO_MODEL_DIR`

CLI flags still take precedence over environment defaults.

## Tooling

This repository uses:

- `uv` for dependency/runtime management
- `ruff` for Python linting/formatting
- `ty` for type checking
- `pytest` for tests
- `prek` for pre-commit hooks
- `just` for task orchestration
- Nix linting parity with `nixos-config`: `statix`, `deadnix`, and `nixfmt --check`

Run local checks:

```bash
just fmt
just fmt-nix
just lint
just test
just smoke-e2e
# or specify a custom asset path (positional args):
just smoke-e2e /path/to/kokoro-82m /tmp/koko-smoke.wav "Koko local inference smoke test"
```

## NixOS / Nix installation

This repo ships a flake package that exposes a `koko` binary.

### Run directly from the repo

```bash
nix run .#koko -- "Hello from nix"
```

### Install to your user profile

```bash
nix profile install .#koko
koko "Installed globally via nix profile"
```

### Add to NixOS system packages (flake-based config)

```nix
{
  inputs.koko.url = "path:/home/rbright/Projects/koko";

  outputs = { self, nixpkgs, koko, ... }: {
    nixosConfigurations.my-host = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ({ pkgs, ... }: {
          environment.systemPackages = [ koko.packages.${pkgs.system}.koko ];
        })
      ];
    };
  };
}
```

## Troubleshooting

- **No audio player found**
  - Install one of: `ffplay`, `aplay`, `paplay`, or use `--no-play --output file.wav`.
- **Offline mode fails with missing assets**
  - Ensure `--model-dir` (or `KOKO_MODEL_DIR`) contains `config.json`, `kokoro-v1_0.pth`, and `voices/*.pt`.
- **You still see Hugging Face requests/warnings**
  - Ensure you are not passing `--no-offline` and that local assets are valid (`config.json`, `kokoro-v1_0.pth`, `voices/*.pt`).
- **CUDA errors**
  - Force CPU mode: `koko --device cpu "hello"`.
- **No input text provided**
  - Provide message args, `--input-file`, or pipe stdin.

## References

- Kokoro GitHub: https://github.com/hexgrad/kokoro
- Kokoro-82M model: https://huggingface.co/hexgrad/Kokoro-82M
- CLI UX inspiration: https://github.com/steipete/sag
