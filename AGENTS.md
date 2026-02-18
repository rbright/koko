# Koko Agent Guide

## Scope
These rules apply to the entire `koko/` repository.

## Mission
Deliver a reliable, offline-first local CLI (`koko`) for Kokoro-82M inference in agentic workflows.

## Instruction Precedence
1. Global agent instructions (`/home/rbright/.pi/agent/AGENTS.md`)
2. This repo guide (`koko/AGENTS.md`)
3. Task-specific source of truth (`README.md`, `justfile`, `flake.nix`, CI workflow)

If rules conflict, prefer the most specific scope.

## Quick Start (Every Task)
1. Read `PLAN.md` and `SESSION.md` before major edits.
2. Keep `PLAN.md` checkboxes current during execution.
3. Record decisions + executed/Skipped verification in `SESSION.md`.
4. Use repo tooling only: `uv`, `ruff`, `ty`, `pytest`, `prek`, `just`.

## Rule Index
| ID | Trigger | Rule |
|---|---|---|
| R1 | CLI UX/runtime changes | Preserve product invariants (on-demand CLI, `af_heart` default, flags-first flow). |
| R2 | Model loading/network behavior | Keep offline-first behavior; outbound access must be explicit (`--no-offline`). |
| R3 | Dependency/packaging changes | Keep Python runtime deps in sync between `pyproject.toml` and `flake.nix`. |
| R4 | CLI refactors | Keep stable entrypoint/import surfaces (`koko_cli.entrypoint:main`, `koko_cli.cli` shim). |
| R5 | Handoff validation | Run full gate relevant to change scope; log anything skipped. |
| R6 | Behavior/config/install changes | Update docs and execution logs (`README.md`, `PLAN.md`, `SESSION.md`). |
| R7 | Any command with side effects | Keep operations safe, explicit, and non-destructive. |

---

## Rule Details

### R1 — Preserve product invariants
- **Scope**: Repo  
- **Problem**: CLI drift (daemonization, changed defaults, inconsistent UX).  
- **Rule**: Keep `koko` on-demand only (no daemon/background service), default voice `af_heart`, and straightforward “flags first, message text last” usage.  
- **Why**: Prevents workflow regressions for agent-driven notifications.  
- **Example**: `koko --voice bf_emma "Task complete"`  
- **When to use**: Any CLI argument, command-shape, or runtime-control change.  
- **Benefits**: Predictable UX and stable automation scripts.

### R2 — Enforce offline-first runtime
- **Scope**: Repo  
- **Problem**: Unintended outbound network calls at runtime.  
- **Rule**: Preserve offline-first behavior. Network-enabled behavior must require explicit user opt-in (`--no-offline`). Keep local asset validation strict (`config.json`, `kokoro-v1_0.pth`, `voices/*.pt`).  
- **Why**: Ensures local-only operation by default.  
- **Example**: If adding remote fallback logic, gate it behind `--no-offline` and keep offline path fail-fast.  
- **When to use**: Model/pipeline/download/runtime path changes.  
- **Benefits**: Privacy, reliability, and predictable execution.

### R3 — Keep dependency + Nix runtime parity
- **Scope**: Repo  
- **Problem**: Nix builds fail when Python runtime deps diverge from `pyproject.toml` constraints.  
- **Rule**: For new runtime imports, update both:
  - `pyproject.toml` dependencies
  - `flake.nix` `propagatedBuildInputs`
  Prefer compatible minimum versions over overly strict pins when Nix package versions lag.
- **Why**: Prevents `pythonRuntimeDepsCheck` failures and packaging drift.  
- **Example**: Add `pydantic-settings` to both `pyproject.toml` and `pythonPackages.pydantic-settings`.  
- **When to use**: Dependency, packaging, or import graph changes.  
- **Benefits**: Reproducible local + Nix behavior.

### R4 — Preserve CLI entrypoint stability during refactors
- **Scope**: Repo  
- **Problem**: Refactors can silently break script targets or import-based usage.  
- **Rule**: Keep the install script target on `koko_cli.entrypoint:main`; keep `koko_cli.cli` as a compatibility shim when relocating internals.  
- **Why**: Avoids breakage for downstream callers and packaging hooks.  
- **Example**: Move parsing/dispatch modules, but keep `koko_cli.cli.main` delegating to entrypoint.  
- **When to use**: Module moves, API reorg, command bootstrap changes.  
- **Benefits**: Safer internal evolution with stable external behavior.

### R5 — Run the right validation gate before handoff
- **Scope**: Repo  
- **Problem**: Regressions slip through when checks are partial or inconsistent.  
- **Rule**: Execute the relevant gate before handoff.

**Baseline gate**
```bash
just fmt
just fmt-nix
just lint
just test
```

**When CLI/runtime behavior changed**
```bash
just smoke-e2e
```

**When packaging/deps/entrypoints changed**
```bash
nix build .#koko
nix run .#koko -- --help
```

**When docs/instruction files changed**
```bash
python3 ~/.agents/skills/update-docs/check-doc-links.py
```

If any check is skipped, log exact command + reason in `SESSION.md`.

- **Why**: Keeps handoffs trustworthy and reproducible.  
- **When to use**: Every delivery; select additional checks by change type.  
- **Benefits**: Fewer CI surprises and faster reviews.

### R6 — Keep docs + execution logs aligned with behavior
- **Scope**: Repo  
- **Problem**: Behavior changes without docs/log updates cause drift and rework.  
- **Rule**: Update `README.md` for behavior/flags/install changes; update `PLAN.md`/`SESSION.md` with what was executed, decisions made, and unresolved risks.  
- **Why**: Maintains accurate repo memory and onboarding quality.  
- **Example**: New env var or flag => document it in `README.md` and record verification in `SESSION.md`.  
- **When to use**: Any user-visible behavior/config/workflow change.  
- **Benefits**: Clear handoff context and less duplicated rediscovery.

### R7 — Safety and side-effect discipline
- **Scope**: Repo  
- **Problem**: Hidden/destructive operations and secret leakage.  
- **Rule**: Do not add secrets or host-specific credentials. Keep file writes/playback/model downloads explicit in code and docs. Avoid destructive shell operations unless explicitly requested.  
- **Why**: Protects developer machines and user trust.  
- **Example**: Prefer explicit output paths and documented side effects.  
- **When to use**: Any command or code path with external effects.  
- **Benefits**: Safer, auditable changes.
