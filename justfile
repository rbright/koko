set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set positional-arguments

tooling_flake := "path:."

default:
    @just --list

# Install/update project dependencies.
deps:
    uv sync --dev

# Format Python code.
fmt:
    uv run ruff format .

# Format tracked Nix files.
fmt-nix:
    nix develop '{{ tooling_flake }}' -c bash -euo pipefail -c 'mapfile -t files < <(rg --files -g "*.nix"); if [[ "${#files[@]}" -eq 0 ]]; then exit 0; fi; nixfmt "${files[@]}"'

# Run lint checks.
lint: lint-ruff lint-ty lint-nix
    @echo "✅ lint passed"

lint-ruff:
    uv run ruff check .

lint-ty:
    uv run ty check .

# Lint Nix configs (statix + deadnix + formatting check).
lint-nix:
    nix develop '{{ tooling_flake }}' -c statix check .
    nix develop '{{ tooling_flake }}' -c bash -euo pipefail -c 'mapfile -t files < <(rg --files -g "*.nix"); if [[ "${#files[@]}" -eq 0 ]]; then exit 0; fi; deadnix --fail --no-underscore "${files[@]}"'
    nix develop '{{ tooling_flake }}' -c bash -euo pipefail -c 'mapfile -t files < <(rg --files -g "*.nix"); if [[ "${#files[@]}" -eq 0 ]]; then exit 0; fi; nixfmt --check "${files[@]}"'

# Run test suite.
test:
    uv run pytest

# Full local gate.
check: lint test
    @echo "✅ check passed"

# Install prek git hooks (pre-commit + pre-push).
precommit-install:
    uv run prek install --hook-type pre-commit --hook-type pre-push

# Run prek hooks over all files for pre-commit stage.
precommit-run:
    uv run prek run --all-files --hook-stage pre-commit

# Run prek hooks over all files for pre-push stage.
prepush-run:
    uv run prek run --all-files --hook-stage pre-push

# Run koko CLI with forwarded args.
run *args:
    uv run koko {{ args }}

# Download Kokoro model assets for local/offline use.
download-model model_dir="~/.local/share/koko/kokoro-82m" voices="all" repo_id="hexgrad/Kokoro-82M":
    uv run koko-download-model --model-dir '{{ model_dir }}' --voices '{{ voices }}' --repo-id '{{ repo_id }}'

# Smoke test with real inference (requires local model assets in offline mode).
smoke-e2e model_dir="~/.local/share/koko/kokoro-82m" output="/tmp/koko-smoke.wav" text="Koko local inference smoke test":
    uv run koko --model-dir '{{ model_dir }}' --no-play --output {{ output }} "{{ text }}"

# Smoke test with LLM summarization enabled (local OpenAI-compatible endpoint).
smoke-llm model_dir="~/.local/share/koko/kokoro-82m" llm_base_url="http://127.0.0.1:11434/v1" llm_model="mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q6_K" output="/tmp/koko-llm-smoke.wav" text="### Build\n- tests passed\n- changed 14 files":
    uv run koko --model-dir '{{ model_dir }}' --summarize --llm-base-url '{{ llm_base_url }}' --llm-model '{{ llm_model }}' --no-play --output {{ output }} "{{ text }}"
