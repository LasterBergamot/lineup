---
paths:
  - "backend/pyproject.toml"
  - "backend/lineup/document/pdf_converter.py"
---

# Backend: security lint (ruff `S` / flake8-bandit)

Paths are relative to `backend/`.

- `[tool.ruff.lint] extend-select = ["S", "D1"]` in `pyproject.toml` enables flake8-bandit checks and pydocstyle's *missing docstring* checks (D100-D107 only, no style rules) as part of `task lint`. `tests/**` and `alembic/versions/*.py` are exempt from `D1`.
- `per-file-ignores` suppresses `S101` (`assert`) and `S310` (`urlopen` scheme check) for `tests/**` — both are expected patterns in test code (pytest's `assert` idiom; `S310` flags a fixed local `BASE_URL` constant, never user input), not real risks.
- `per-file-ignores` also suppresses `S603`/`S607` (subprocess call / partial executable path) for `lineup/document/pdf_converter.py` specifically — its one `subprocess.run([...])` call uses a literal `"libreoffice"` executable and an argv list with no `shell=True`, and every other argument is either a fixed flag or built from a `tempfile.TemporaryDirectory()` the process created itself, so neither warning reflects a real vulnerability there. Don't remove this ignore to "fix" the warning without addressing why it was added — re-read this note first.
- If a *new* `S`-rule violation appears anywhere outside these two ignored spots, treat it as a real finding: fix the underlying code rather than reflexively adding another ignore.
