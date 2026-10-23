# DD-100 — notes for Claude Code

This repo is a due-diligence harness for crypto projects. When asked to
evaluate, diligence or score a project, follow `skills/crypto-dd/SKILL.md`
(also available as the project skill `crypto-dd` under `.claude/skills/`).

## Layer separation — do not blur it
- `framework/`, `config/` — the contract. Thresholds, weights, gates. Change
  them only when the user asks to change the methodology, and run the tests.
- `dd100/` — deterministic code. No thresholds or numbers hard-coded here.
  The only model call is `dd100/evaluators/llm.py`, behind `--llm`.
- `projects/<slug>/` — one folder per project under review: manifest,
  evidence packs, assessments, generated report.

## Commands
```
python -m dd100 validate
python -m dd100 template projects/<slug>
python -m dd100 collect projects/<slug>/manifest.yaml
python -m dd100 run projects/<slug>/manifest.yaml
python -m pytest -q
```

## Rules when working on a review
- Never edit generated files in `report/`; re-run the harness.
- Never change an assessment's score to get it past validation; fix the evidence.
- Never fill T02, M05 or L07 — they are human-only.
- If a gate fires, report it. Do not adjust inputs to clear it.
- After changing `framework/`, regenerate `skills/crypto-dd/references/metrics-catalog.md`
  with `python -m dd100 metrics`.
