#!/usr/bin/env python3
"""Run all code quality checks and tests."""

import os
import subprocess
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Colors for terminal output (simplified for Windows compatibility)
try:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CHECK = "✓"
    CROSS = "✗"
    ARROW = ">"
except (UnicodeEncodeError, UnicodeDecodeError):
    # Fallback for systems that don't support Unicode/ANSI colors
    GREEN = YELLOW = RED = RESET = BOLD = ""
    CHECK = "[OK]"
    CROSS = "[FAIL]"
    ARROW = ">"


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{BOLD}{YELLOW}{ARROW} {description}{RESET}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"{GREEN}{CHECK} {description} passed{RESET}")
        return True
    except subprocess.CalledProcessError:
        print(f"{RED}{CROSS} {description} failed{RESET}")
        return False
    except FileNotFoundError:
        print(f"{RED}{CROSS} Command not found: {cmd[0]}{RESET}")
        return False


def main():
    """Run all checks and tests."""
    print(f"{BOLD}{'='*60}")
    print("Running All Code Quality Checks and Tests")
    print(f"{'='*60}{RESET}\n")
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    checks = [
        (["black", "--check", "app", "config", "tests"], "Black (format check)"),
        (["flake8", "app", "config", "tests"], "Flake8 (linting)"),
        (["mypy", "app", "config"], "MyPy (type checking)"),
        (["pytest", "--cov=app", "--cov=config", "--cov-report=term-missing", "-v"], "Pytest (tests with coverage)"),
    ]
    
    results = []
    for cmd, description in checks:
        success = run_command(cmd, description)
        results.append((description, success))
    
    # Summary
    print(f"\n{BOLD}{'='*60}")
    print("Summary")
    print(f"{'='*60}{RESET}\n")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = f"{GREEN}{CHECK} PASSED{RESET}" if success else f"{RED}{CROSS} FAILED{RESET}"
        print(f"  {status} - {description}")
    
    print(f"\n{BOLD}Total: {passed}/{total} checks passed{RESET}\n")
    
    if passed == total:
        print(f"{GREEN}{BOLD}All checks passed! {CHECK}{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}Some checks failed. Please fix the issues above.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
