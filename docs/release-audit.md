# SLOKern Public Release Repository Hygiene Audit

**Audit date:** 2026-10-30  
**Scope:** Current checkout, Git index, manifests, CI, scripts, tests, documentation links, ignores, local generated directories, and tracked-file secret scan.  
**Mode:** Read-only audit. No tracked file was removed, moved, or rewritten. This report is the only file added by the audit.  
**Working-tree caveat:** The checkout already had edits in API routes/app, frontend API/types, and an untracked API test. Those changes were preserved and were not treated as release-audit changes.

## Executive assessment

The tracked source set is compact (297 files across source, tests, contracts, fixtures, docs, frontend, and CI). Local environments, caches, `artifacts/`, `scratch/`, and copied tooling are ignored rather than tracked. The recent tooling removal is present in Git history; local copies remain ignored. No history rewrite or cleanup was performed.

The repository is **not release-ready without follow-up**. Main risks are stale/contradictory README and status claims, placeholder commands in the README that do not match the current CLI, no functioning demo runner/Makefile/pre-commit hooks, CI not exercising the frontend or the lint/type/schema/secret checks its header describes, inconsistent Python install locking, an `.env.example` workflow that conflicts with explicit secrets-file discovery, and a tracked-file secret scanner that currently reports three benign placeholder/test-string false positives. `git diff --check` also reports trailing whitespace in an existing user-edited API route; it was left untouched.

## Classification legend and coverage

- **RETAIN:** Required or useful source, tests, contracts, reproducibility, licensing, or release evidence.
- **CONSOLIDATE:** Retain content, but merge overlapping status/reference material after owners choose a canonical location.
- **EXCLUDE:** Keep locally or in development history; keep out of the public release surface/archive.
- **DELETE candidate:** Evidence supports that a file is inert or obsolete; remove only after approval and any needed history preservation.
- **MOVE:** Keep the material, but separate internal engineering or historical content from user-facing docs.

The audit classified all 297 tracked paths by top-level area and the significant root files below. A path not listed as a removal candidate is retained by default. Ignored/untracked local directories are classified separately; they are not part of the current GitHub tree.

## Top-level directory classification

| Path | Classification | Evidence and recommendation |
|---|---|---|
| `.agent/`, `.agents/`, `.codex/`, `.impeccable/`, `.Jules/` | EXCLUDE | Local agent/design tooling; Git ignore rules cover these. The formerly tracked `.agents` audit helper was removed in commit history and is now ignored locally. `ROADMAP.md` still cites that local-only helper; replace the citation with committed test evidence before release. |
| `.git/` | RETAIN | Git object database and complete development history. Do not prune or rewrite history. |
| `.github/` | RETAIN | Contains CI workflow, CODEOWNERS, and PR template. CI coverage gaps are listed below. |
| `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` | EXCLUDE | Generated local caches; ignored. Present locally at approximately 10 MiB combined. |
| `.venv/`, `venv/` | EXCLUDE | Local Python environments; ignored. Present locally at approximately 162 MiB combined. Recreate from documented installation steps. |
| `.vscode/`, `.mcp.json`, root `skills-lock.json` | EXCLUDE | Local editor/MCP/agent dependency metadata. These are no longer tracked and remain ignored locally. `git archive` excludes tracked counterparts by attributes. |
| `artifacts/` | EXCLUDE, with selective evidence retention | 878 local files, approximately 2.6 MiB; ignored and not in Git. Preserve locally. Select only small, sanitized, deterministic demo evidence for release fixtures; do not publish raw runs without privacy and provenance review. |
| `assets/` | RETAIN pending ownership check | Contains one 1.27 MiB PNG logo. No references were found in README/docs/frontend/source/tests in this scan. Confirm whether it is a required brand asset and verify authorship/license before removing or shipping. |
| `docs/` | RETAIN / CONSOLIDATE / MOVE | Keep technical definitions, ADRs, compliance evidence, deployment and user guides. Consolidation and internal/archive moves are proposed below; preserve dated evidence. |
| `experiments/` | RETAIN | Versioned search-space, policy, protocol, and example configs are reproducibility inputs. |
| `fixtures/` | RETAIN | Small demo, evidence, workload, and golden metric fixtures used by tests and examples. Preserve `DEMO DATA` labeling. |
| `frontend/` | RETAIN | Application source, package manifest, npm lockfile, build configs, and frontend README are required. Exclude local `node_modules/` and `dist/`; both are ignored. Local frontend tree is approximately 72 MiB, including generated/dependency content. |
| `results/` | EXCLUDE | Local output placeholder only; no tracked content was found. Keep generated results out of source unless a specific sanitized result is intentionally added as a fixture. |
| `schemas/` | RETAIN | Generated JSON contracts are checked by contract tests and must ship with the source. `.gitkeep` is redundant while schema files are tracked; removal is optional and low priority. |
| `scratch/` | EXCLUDE, preserve locally | Seven ignored one-off audit/patch scripts (~0.03 MiB). No current runtime, package, test, or CI dependency was found. Do not delete as part of release cleanup; retain local/historical copies or archive them outside the release bundle. |
| `scripts/` | RETAIN; review inert runner | Retain contract generator, demo/preflight/smoke runners, and secret scanners. `scripts/demo_run.py` is currently only a docstring, has no discovered callers, and does not provide the demo behavior implied by its name; see delete candidates. |
| `src/` | RETAIN | Application packages and runtime code. Do not remove unused-looking modules without import/call/reference analysis. |
| `tests/` | RETAIN | Unit, contract, integration, and live tests are release confidence and evidence; no tests are proposed for removal. Includes one untracked user-owned API test in this checkout; preserve it. |

## Significant root-file classification

| File | Classification | Finding |
|---|---|---|
| `README.md` | RETAIN / CONSOLIDATE | Main public entry point, but its sample `smoke-test`, `verify`, `report`, and optimize flags/arguments do not consistently match current CLI syntax. Reconcile examples against `slokern --help` before release. |
| `LICENSE` | RETAIN | Apache 2.0 license is present. Keep copyright and attribution intact. |
| `pyproject.toml` | RETAIN | Runtime and dev dependency source and console entry point. Runtime dependency is Pydantic v2; dev extras declare pytest/ruff/mypy. No Python lockfile is tracked. |
| `frontend/package.json`, `frontend/package-lock.json` | RETAIN | npm is the frontend package manager in current docs and lockfile. Prefer `npm ci` for clean, reproducible CI/release builds. Do not add the ignored pnpm lockfile. |
| `.env.example` | RETAIN after correction | Contains an empty placeholder, no credential. It instructs copying to `.env`, but startup discovery no longer searches implicit `.env`; document `SLOKERN_SECRETS_FILE` or remove the misleading copy workflow. |
| `.gitignore` | RETAIN / SIMPLIFY | Covers caches, environments, artifacts, and local tooling. It has a redundant `.agents` negation immediately canceled by a later ignore rule, plus scattered one-off local paths; simplify after approval. |
| `.gitattributes` | RETAIN | `export-ignore` excludes local tooling from `git archive`; tracked files have since also been removed from the Git index. Keep attributes as defense in depth. |
| `.github/workflows/ci.yml` | RETAIN / UPDATE | Runs backend install, `pip check`, `compileall`, import smoke, and `pytest -m "not live"`. It does not build/test the frontend, run ruff/mypy, check generated schemas, or run the secret scanner, despite its header describing those checks. |
| `.pre-commit-config.yaml` | DELETE candidate or implement | Contains comments only; there are no hooks. Either wire real hooks or remove this inert file. |
| `Makefile` | DELETE candidate or implement | Contains comments only; it defines no targets. Either add useful documented targets or remove it. |
| `tsconfig.json` | RETAIN | Root project references `frontend/tsconfig.app.json` and `frontend/tsconfig.node.json`; it is not an orphan. |
| `AGENTS.md` | MOVE / review | Internal contributor and agent operating guidance, not required at runtime. Move to `docs/internal/` or keep as a clearly contributor-facing root policy; reconcile obsolete/stale implementation claims first. |
| `ROADMAP.md` | MOVE / CONSOLIDATE | Useful internal execution history, but large and status-heavy. Keep full history in Git; consider moving under `docs/internal/` and make current state link to the blocker register and implementation status. Remove references to untracked agent-only evidence. |
| `PRODUCT.md` | CONSOLIDATE | Product brief overlaps README positioning, personas, workflow, and requirements. Preserve unique product decisions, but avoid maintaining duplicated claims in two public entry points. |
| `DESIGN.md` | MOVE | Detailed visual/design system is internal product design material; move under `docs/design/` if still actively used. Preserve it if the shipped frontend relies on these tokens and principles. |
| `final_report.md`, `patch_scan_secrets.py`, `update_roadmap.py` | EXCLUDE / DELETE candidates | Local ignored files, not tracked. The patch scripts rewrite tracked documentation/security files; no runtime/package/test/CI callers were found. Preserve copies for history, then delete locally only after owner approval. `final_report.md` should be reviewed for sensitive or stale claims before any intentional release. |
| Root `skills-lock.json`, `.mcp.json`, `.vscode/settings.json` | EXCLUDE | Agent/MCP/editor metadata. Removed from GitHub in prior commits and now ignored locally; retain local copies if useful. |

## Recommended deletions (approval required; none executed)

1. **`scripts/demo_run.py`** — source is a docstring only, no entrypoint behavior, and no references were found. It is not a functioning feature. Delete only after replacing any expectation of this runner with an actual documented demo command or explicitly removing the expectation.
2. **`Makefile`** — comment-only, no targets or discovered references. Remove or implement useful targets.
3. **`.pre-commit-config.yaml`** — comment-only, no hooks. Remove or configure hooks that are actually maintained.
4. **`schemas/.gitkeep`** — redundant because generated schema JSON files are tracked. Low-impact cleanup only.
5. **Local `patch_scan_secrets.py`, `update_roadmap.py`, and `scratch/patch_*.py`** — one-off mutating scripts, ignored/untracked, and no source/CI/test/package references found. They are not part of GitHub now. Retain local/historical copies until approved for deletion; do not import them into the release bundle.

No application source, test, generated contract, schema, or historical Git commit is recommended for removal. The logo is an unresolved asset decision, not a deletion recommendation.

## Documentation consolidation and separation

- Establish clear roles: `README.md` for public quickstart and actual supported workflow; `docs/architecture.md` for stable architecture; `docs/decision-log.md` as an ADR index or consolidate it with `docs/adr/`; `docs/blocker-register.md` for active blocker state; `docs/implementation-status.md` for observed implementation and validation; `ROADMAP.md` for dated task/history.
- `docs/project-flow-and-mental-model.md` overlaps the architecture overview and pipeline sections. Merge unique concepts into architecture, then keep a short link/index or archive the redundant guide.
- `docs/mvp-checklist.md`, `docs/integration-checklist.md`, and `docs/final-integration-plan.md` overlap acceptance gates, validation steps, and release tasks. Preserve all historical decisions/evidence, but choose one current acceptance checklist and move dated plans/snapshots into `docs/archive/` rather than deleting them.
- `PRODUCT.md` overlaps README product positioning. `DESIGN.md` is useful but internal; move it to `docs/design/` if still authoritative.
- `docs/adr/0001-model-runtime.md` and `docs/adr/0001-mvp-scope-and-evidence.md` share ADR number `0001`. Resolve numbering and cross-links without dropping either decision.
- Several docs contain stale states and instructions. In particular, implementation-status text contradicts other documents and the current checkout; the README includes outdated report/verify command shapes; `docs/deployment.md` describes `.env` generally while the loader requires an explicitly configured path. Add a docs-link/CLI-help check to CI after content is reconciled.

## `.gitignore` and release archive improvements

Current coverage is generally good: Python caches and venvs, frontend `node_modules`/`dist`, secrets, artifacts, editor files, scratch, MCP, and skills locks are ignored. The `.gitattributes` export rules cover selected tooling and build output.

Recommended follow-up:

- Simplify the duplicate `.agents/teamwork/...` allow-then-ignore rules; the current result is ignored, but the intent is hard to read.
- Ignore common generated outputs consistently (`coverage/`, `.coverage*`, `*.egg-info/`, `build/`, `dist/`, OS/editor files) at the root and frontend scopes where appropriate.
- Add `.env.*` rule with explicit allowlist for `.env.example` if local environment variants are used; ensure no actual secret file is tracked.
- Keep `artifacts/`, `scratch/`, local venvs, caches, and generated UI build output out of Git. Do not blanket-ignore fixtures or schemas.
- Review `git check-ignore -v` for each proposed path and `git ls-files` for already-tracked files; ignore rules do not untrack content.
- Use `git archive` export-ignore only for actual archive packaging; it does not affect GitHub repository contents or clones. The removed tooling is already absent from the tracked tree.

## Release directory structure proposal

```text
README.md                 public product, quickstart, truthful capabilities
LICENSE                   Apache 2.0
pyproject.toml             Python package and entry point
src/slokern/               application source
schemas/                   generated contract schemas
fixtures/                  small sanitized demo/test evidence
experiments/                versioned configs, policies, protocols
frontend/                   source, package.json, package-lock.json
scripts/                    maintained generation, scanning, smoke, demo utilities
tests/                      unit, contract, integration, and gated live tests
.github/                    CI, ownership, PR template
docs/                       user docs, architecture, methodology, compliance
docs/internal/              contributor policy, roadmap/status, ownership
docs/archive/               dated plans and historical evidence retained
```

Treat this as a target layout, not an instruction to move files in this audit. Do not move source, fixtures, schemas, or historical records until references and packaging paths are updated and validated.

## Dependency and artifact hygiene

- **Python:** `pydantic>=2,<3` is the only runtime dependency. `pytest`, `ruff`, and `mypy` are development dependencies. Ruff/mypy are declared but not executed by current CI; either add CI jobs or remove them from the advertised required workflow after an owner decision. No evident unused runtime dependency was found by manifest/source inspection.
- **Python reproducibility:** No Python lock/constraints file is tracked. CI resolves open version ranges on each run. Decide whether this project needs a lock (e.g. uv lock) or a documented tested version matrix; current docs mention both `pip` and `uv` inconsistently.
- **Frontend:** `package-lock.json` is present and npm is documented. Use `npm ci` in CI for lockfile enforcement. The untracked/ignored pnpm lockfile must not be added while npm is canonical.
- **Tracked artifacts:** 297 tracked files include only small fixtures/schemas and one 1.27 MiB logo; no benchmark output directory is tracked. Local `artifacts/` has 878 files/2.6 MiB and remains ignored. Inspect only selected, sanitized evidence for intentional release inclusion.
- **Generated data:** Keep 11 JSON schemas generated from Pydantic contracts; run `scripts/gen_contracts.py --check` in release validation. Do not hand-edit or delete schemas to reduce size.
- **Build outputs/caches:** `.venv`, `venv`, frontend dependencies/build, Python caches, local artifacts, agent tooling, and scratch occupy substantial local disk but are ignored. No deletion was performed.

## Security findings

- The tracked `.env.example` contains an empty placeholder only. No key value is present there.
- `scripts/scan_secrets.py` was run against tracked files. It reported **3 potential matches**: two setup examples containing `your-actual-api-key` in `src/slokern/config/secrets.py` and one dummy parser-test value in `tests/unit/config/test_secrets.py`. These are benign placeholders/test data, not observed credentials; the scanner currently does not exempt these forms. Scanner result is therefore **FAIL (false positives requiring scanner/test-fixture review)**, not a clean pass.
- `git status` contains user changes to API/frontend source and an untracked API test. No values were emitted or inspected as credentials. Preserve these changes and review them separately before commit.
- Root `.mcp.json` is local and ignored; do not add it to release. Scan/verify that local file privately if it is ever intentionally published; this report does not reproduce its contents.
- Credential bootstrap on Windows does not validate ACLs for local secret files; the documented safe path is environment or an OS credential store. Keep this limitation visible.
- No tracked API keys, private keys, or secret-bearing benchmark outputs were identified by the scanner; scanner false positives prevent claiming a clean automated secret scan.
- License: Apache 2.0 `LICENSE` is present. Confirm the logo’s origin/license before public redistribution; retain upstream dependency attributions and the package author attribution.

## Validation and audit evidence

- **Inventory:** `git ls-files` reported 297 tracked paths. Root and significant subdirectories were classified above; local ignored directory sizes were inventoried without modifying them.
- **References:** Searched tracked/source/docs/CI references for patch scripts, scratch, demo runner, assets, lockfiles, and installation commands. A best-effort relative Markdown-link scan found **0 missing local targets**.
- **Secret scan:** `.venv\Scripts\python.exe scripts\scan_secrets.py` returned **FAIL: 3 potential matches**, all placeholder/test strings listed above.
- **Diff check:** `git diff --check` reported one trailing-whitespace line in `src/slokern/api/routes/reports.py:41`, part of existing user work; left unchanged. Git also emitted line-ending notices for other modified user files.
- **Tests/builds:** Not run. This was a read-only release audit; no approved modifications have been applied.

## Risks and unresolved decisions

1. Are serverless live baseline plus independent verification and fake-only candidate search acceptable for the hackathon MVP, given BLK-17? Current managed endpoint cannot tune/read back the search dimensions.
2. Which document is the canonical status source? Current README, roadmap, implementation status, and blocker register contain stale/contradictory statements.
3. Should the internal agent/contributor policy and large roadmap ship in the public repository, move under `docs/internal/`, or be retained at root for contributors?
4. Is `assets/slokern_logo.png` owned/licensed for redistribution and actually needed?
5. Should Python dependencies be pinned with a lock/constraints file, and should CI enforce frontend build, ruff, mypy, generated schema drift, and secret scanning?
6. Is the Windows local-secret-file path to be supported after ACL validation, or explicitly unsupported in release docs?
7. The current CLI examples in README are stale; public release instructions must be corrected before tagging.
8. Full-suite completion, live Nebius verification, and end-to-end clean-clone setup are not established by this audit.

## Final release-readiness checklist

- [ ] Confirm MVP evidence strategy and BLK-17 handling.
- [ ] Reconcile README commands with current `slokern --help`; correct `.env.example`/secret setup instructions.
- [ ] Choose canonical status docs; preserve dated plans and history while consolidating duplicates.
- [ ] Remove the stale roadmap reference to a local-only agent audit, or replace it with committed, reproducible evidence.
- [ ] Decide logo attribution and whether to ship it.
- [ ] Decide whether to remove or implement inert `scripts/demo_run.py`, `Makefile`, and pre-commit configuration.
- [ ] Add Python dependency reproducibility policy and npm `npm ci` build/test to CI.
- [ ] Add schema-current and scanner checks to CI; fix scanner false positives without broadening exemptions unsafely.
- [ ] Run clean-clone Python install, frontend `npm ci` + build/test, full offline suite, contract drift, and secret scan; record exact outputs.
- [ ] Verify release archive excludes local tooling and generated outputs; confirm Apache license and asset attribution.
- [ ] Review working-tree changes separately; do not include unrelated API/frontend edits without owner review.
- [ ] Tag only after live-vs-demo claims, model eligibility, and evidence limitations are documented accurately.

**Release verdict:** **NOT READY for a public release tag yet.** Repository history and core files are intact, but stale instructions/status, CI coverage gaps, unresolved attribution, false-positive secret scan, and incomplete full/live validation remain. No destructive cleanup has been applied; approval is required before the proposed deletions, moves, or ignore-rule changes.
