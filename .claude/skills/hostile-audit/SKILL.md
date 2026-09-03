---
name: hostile-audit
description: >
  Adversarial audit of code, tests, or CI in plugin.video.mubi. Use when asked
  to audit, red-team, bug-hunt, stress-test, break, review, or "find what's
  wrong with" a file, module, diff, PR, or the whole repo. A finding is reported
  only after it is reproduced (a throwaway pytest that fails, a static fact from
  a command) or explicitly reasoned from the callers; hypotheses are dropped.
  Gated workflow: scope -> context -> audit -> report -> apply. Findings are
  severity-rated (S1/S2/S3), each carries an exact fix, a regression-test name,
  and one prevention mechanism. Never applies fixes without the typed token.
argument-hint: "[path | module | diff | pr <n> | repo] [--fix]"
---

# Hostile audit

You are an adversary with read access. Make the code fail, then prove it.
Rationale for the rules the audit enforces lives in `CLAUDE.md` and `docs/DEVELOPMENT_PRINCIPLES.md`.

## Principles

| # | Rule |
|---|---|
| P1 | Assume every line is wrong until a run proves it right. |
| P2 | Every finding cites exact `file:line` and is CONFIRMED (a run demonstrates the defect) or PLAUSIBLE (reasoned from callers, could not run in-process). One bullet per checklist item; never aggregate. |
| P3 | Every CONFIRMED finding carries an exact fix sketch, a named regression test, and exactly one prevention mechanism. "Be more careful" is not prevention. |
| P4 | Never apply a fix without `--fix` in the invocation or the typed token `APPROVE FIXES` in a prior turn. |
| P5 | Never edit a CODEOWNERS-protected file (`backend/schemas/`, `tests/backend/test_schema_v1.py`) silently — say so and stop. |
| P6 | A "fake / tautological test" claim must be proven by mutation: break the code, run the test, record whether it caught it. Never assert it from reading. |

## Output

Single report file, grown per step: `tmp/YYYYMMDD-HHMMSS-hostile-audit-<target>.md` (`tmp/` is gitignored; `mkdir -p tmp` if absent). Reproduction scripts go beside it as `tmp/YYYYMMDD-HHMMSS-audit-<topic>.py` and are left in place so a finding can be re-run.

**Context recovery:** on resume, read the newest matching report in `tmp/` and continue from the last completed step header.

## Workflow

| Step | Name | Gate |
|---|---|---|
| 1 | Scope & inventory | ⛔ `APPROVE SCOPE` / `NARROW: <subset>` — required only for `repo` or >5 files; a single file/module/diff/PR states scope in one line and proceeds |
| 2 | Gather context | auto |
| 3 | Audit | auto |
| 4 | Report | auto — this is the deliverable |
| 5 | Apply fixes | ⛔ `--fix` or `APPROVE FIXES` |

Read the reference for a step BEFORE executing it.

| Step | Read first |
|---|---|
| 1, 2, 4, 5 | `references/workflow.md` |
| 3 | `references/workflow.md` (ledger, disclosure, mutation protocol) + `references/checklist.md` |
| severity / escalate / anti-patterns / accepted risks | `references/severity-antipatterns.md` |

## Checklist section index

Never run Step 3 from this index alone — read `references/checklist.md` first.

| Sec | Content |
|---|---|
| A | Data & API contract (A1–A9) |
| B | Time & availability (B1–B5) |
| C | Filesystem & library (C1–C8) |
| D | Concurrency & process model (D1–D5) |
| E | Kodi environment & settings (E1–E9) |
| F | Data flow & schema versioning (F1–F6) |
| G | Backend pipeline (G1–G7) |
| H | CI & release (H1–H7) |
| I | Security & secrets (I1–I5) |
| J | Test quality — only when auditing tests (J1–J6) |

Applicability by target:

| Sec | plugin `.py` | backend `.py` | `.yml` workflow | tests |
|---|:---:|:---:|:---:|:---:|
| A | ✓ | ✓ | — | — |
| B | ✓ | ✓ | — | — |
| C | ✓ | — | — | — |
| D | ✓ | ✓ | — | — |
| E | ✓ | — | — | — |
| F | ✓ | ✓ | — | — |
| G | — | ✓ | — | — |
| H | — | — | ✓ | — |
| I | ✓ | ✓ | ✓ | — |
| J | — | — | — | ✓ |
