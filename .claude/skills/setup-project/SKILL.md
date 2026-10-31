---
name: setup-project
description: Set up the lineup project from a fresh clone — install prerequisites, dependencies, build the container, run migrations, and verify everything works. Use when the repo has just been cloned and nothing is installed yet, or when helping someone get a working dev environment.
model: haiku
effort: high
---

Follow `documentation/Setup.md` from the top. It is the single source of truth for setting up
this repo, shared with people and other AI agents, so do not work from memory or from an older
copy of these steps.

- Read the whole page first, including **Ground rules**, and keep to them.
- Do the steps in order. After each one, compare the output with its **Expected** line. If it
  doesn't match, stop, and tell the user the step, the exact command and its output.
- Skip the optional steps (3, 6, 8) unless the user asked for what they set up. Ask before
  step 7, because it stops a running container.
- Finish with the report described in the ground rules.

If the page looks wrong or out of date, say so and fix the page, not this skill.
