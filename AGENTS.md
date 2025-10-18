# AGENTS.md — Guardrails for Codex

## Project
Name: {{PROJECT_NAME}}
Primary language(s): {{LANGS}}
Package manager(s): {{PKG_MGRS}}
OS/Shell assumptions: {{OS}} / {{SHELL}}

## Working Directory & Paths
- Treat the repo root as the only working directory: `{{REPO_ROOT}}` (relative `/` = repo root).
- Create or modify files **only** within these whitelisted paths:
  - `{{REL_PATH_1}}/`
  - `{{REL_PATH_2}}/`
- Never write outside these paths. Never create new top-level folders unless explicitly listed above.
- If a path is missing, STOP and ask for confirmation instead of creating a sibling or parent directory.

## Build & Test
- Install: `{{INSTALL_CMD}}`
- Lint: `{{LINT_CMD}}`
- Tests: `{{TEST_CMD}}` (must pass)
- Typecheck (if any): `{{TYPECHECK_CMD}}`

## Edit Discipline
- Before changes: print `pwd` and `ls -la` to confirm location.
- After changes: show `git status --porcelain` and a unified diff of all edits.
- Only include code in files; avoid updating docs/tests unless requested.

## Commit Protocol
- Single atomic commit per task with message:
  `{{COMMIT_PREFIX}}: {{ONE_LINE_SUMMARY}}`
  Body: rationale and links to relevant code sections.

## Safety
- Do not rename/move files unless the task says so.
- If tests fail, revert the last change and try again or ask for help.
