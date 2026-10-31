---
name: setup-project
description: Set up the project from a fresh clone by following its setup runbook — check the tools, install dependencies, run the tests, start the services, and verify each step. Use when the repo has just been cloned and nothing is installed yet, or when helping someone get a working dev environment.
model: haiku
effort: high
---

Follow the project's setup runbook from the top. It is the single source of truth for setting
up the repo, shared with people and other AI agents, so do not work from memory.

Find the runbook: the setup row of the router in `CLAUDE.md` (or `AGENTS.md`), otherwise
`documentation/Setup.md` or `docs/setup.md`. If there is none, say so and stop: offer to write
one instead of improvising the steps.

- Read the whole runbook first, including its ground rules, and keep to them.
- Do the steps in order. After each one, compare the output with its **Expected** result. If
  it doesn't match, stop, and tell the user the step, the exact command and its output.
- Never install system tools yourself and never use `sudo`. Never read `.env` files.
- Skip optional steps unless the user asked for what they set up. Ask before any step that
  stops a running container or service.
- Finish with three lists: installed, running, and failed or skipped. Don't call the setup a
  success unless every step you ran matched its expected result.

If the runbook looks wrong or out of date, say so and fix the runbook, not this skill.
