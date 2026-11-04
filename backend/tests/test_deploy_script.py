"""The behaviour of scripts/deploy.py (`task deploy`, #258): every branch, with nothing real run.

`subprocess.run` is replaced by a recorder, `time.sleep` is skipped, input is scripted, and HOME points
at a throw-away folder, so the real `~/.config/lineup/` is never read. Host names are `lineup.example.com`
only, the same rule the script follows.
"""

import ast
import builtins
import importlib.util
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "deploy.py"
spec = importlib.util.spec_from_file_location("deploy", SCRIPT)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

SSH = "lineup@lineup.example.com"
DIR = "/srv/lineup"
LIST_CMD = [
    "gh",
    "run",
    "list",
    "--workflow=deploy-dev.yml",
    "--branch",
    "develop",
    "--limit",
    "1",
    "--json",
    "databaseId",
    "--jq",
    ".[0].databaseId",
]


class Recorder:
    """Stands in for subprocess.run: each call pops the next queued outcome and records the argv.

    An outcome is an exit code, an (exit code, stdout) pair, or an exception to raise. Once the queue
    is empty a call succeeds with no output.
    """

    def __init__(self):
        self.outcomes = []
        self.calls = []

    def __call__(self, argv, **kwargs):
        assert isinstance(argv, list), "subprocess calls must use an argument list"
        assert kwargs.get("shell", False) is False, (
            "subprocess calls must never use shell=True"
        )
        self.calls.append(argv)
        outcome = self.outcomes.pop(0) if self.outcomes else 0
        if isinstance(outcome, BaseException):
            raise outcome
        code, stdout = outcome if isinstance(outcome, tuple) else (outcome, "")
        return subprocess.CompletedProcess(argv, code, stdout=stdout, stderr="")


class Prompts:
    """Stands in for input(): returns the queued lines in turn, then reports end of input."""

    def __init__(self):
        self.lines = []
        self.asked = []

    def __call__(self, prompt=""):
        self.asked.append(prompt)
        if not self.lines:
            raise EOFError
        return self.lines.pop(0)


class FakeStdin:
    """Stands in for sys.stdin: only `isatty()` matters to the script."""

    def __init__(self):
        self.tty = False

    def isatty(self):
        return self.tty


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """A throw-away HOME, and no inherited settings from the real environment."""
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    monkeypatch.delenv("LINEUP_SELFHOST_SSH", raising=False)
    monkeypatch.delenv("LINEUP_SELFHOST_DIR", raising=False)
    return path


@pytest.fixture(autouse=True)
def run(monkeypatch):
    """Every subprocess call goes to the recorder, so no test can start gh or ssh."""
    recorder = Recorder()
    monkeypatch.setattr(deploy.subprocess, "run", recorder)
    return recorder


@pytest.fixture(autouse=True)
def prompts(monkeypatch):
    """Every input() goes to the scripted prompts; by default the answer is end of input."""
    scripted = Prompts()
    monkeypatch.setattr(builtins, "input", scripted)
    return scripted


@pytest.fixture(autouse=True)
def stdin(monkeypatch):
    """Not a terminal unless a test sets `tty = True`."""
    fake = FakeStdin()
    monkeypatch.setattr(sys, "stdin", fake)
    return fake


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    """Record the waits instead of sleeping."""
    waited = []
    monkeypatch.setattr(deploy.time, "sleep", waited.append)
    return waited


def write_settings(text, mode=0o600):
    """Write the per-user settings file under the throw-away HOME, with the given mode."""
    path = deploy.settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)
    return path


def set_local_env(monkeypatch, ssh=SSH, directory=DIR):
    """Set both self-hosted settings in the environment."""
    monkeypatch.setenv("LINEUP_SELFHOST_SSH", ssh)
    monkeypatch.setenv("LINEUP_SELFHOST_DIR", directory)


class TestTargetChoice:
    def test_without_a_terminal_and_no_target_is_a_usage_error(
        self, run, prompts, capsys
    ):
        assert deploy.main([]) == 2
        assert run.calls == []
        assert prompts.asked == []
        assert "--cloud" in capsys.readouterr().err

    def test_yes_does_not_choose_a_target_without_a_terminal(self, run):
        assert deploy.main(["--yes"]) == 2
        assert run.calls == []

    def test_menu_choice_1_is_the_cloud(self, run, prompts, stdin, capsys):
        stdin.tty = True
        prompts.lines = ["1", "yes"]
        run.outcomes = [0, (0, "42\n"), 0]
        assert deploy.main([]) == 0
        assert run.calls[0][:3] == ["gh", "workflow", "run"]
        assert "1) cloud" in capsys.readouterr().err

    def test_menu_choice_2_is_the_local_machine(self, run, prompts, stdin, monkeypatch):
        stdin.tty = True
        set_local_env(monkeypatch)
        prompts.lines = ["2", "yes"]
        assert deploy.main([]) == 0
        assert run.calls[0][0] == "ssh"

    def test_a_menu_answer_other_than_1_or_2_aborts(self, run, prompts, stdin, capsys):
        stdin.tty = True
        prompts.lines = ["3"]
        assert deploy.main([]) == 1
        assert run.calls == []
        assert "Aborted: nothing was changed." in capsys.readouterr().err

    def test_end_of_input_at_the_menu_aborts(self, run, stdin, capsys):
        stdin.tty = True
        assert deploy.main([]) == 1
        assert run.calls == []
        assert "Aborted: nothing was changed." in capsys.readouterr().err

    def test_cloud_and_local_together_are_refused(self):
        with pytest.raises(SystemExit) as refused:
            deploy.main(["--cloud", "--local"])
        assert refused.value.code == 2

    @pytest.mark.parametrize("bad", ["1.2.3", "v1.2", "v1.2.3; rm -rf ~", "latest"])
    def test_version_must_be_a_release_tag(self, bad):
        with pytest.raises(SystemExit) as refused:
            deploy.main(["--local", "--version", bad])
        assert refused.value.code == 2

    def test_version_with_the_cloud_is_refused_and_nothing_runs(self, run, capsys):
        assert deploy.main(["--cloud", "--version", "v1.2.3", "--yes"]) == 2
        assert run.calls == []
        assert "--local" in capsys.readouterr().err


class TestConfirmation:
    def test_a_typed_yes_in_any_case_continues(self, run, prompts):
        prompts.lines = ["  YES "]
        run.outcomes = [0, (0, "7\n"), 0]
        assert deploy.main(["--cloud"]) == 0
        assert len(run.calls) == 3

    def test_anything_else_aborts_without_running(self, run, prompts, capsys):
        prompts.lines = ["no"]
        assert deploy.main(["--cloud"]) == 1
        assert run.calls == []
        assert "Aborted: nothing was changed." in capsys.readouterr().err

    def test_end_of_input_counts_as_no(self, run, capsys):
        assert deploy.main(["--cloud"]) == 1
        assert run.calls == []
        assert "--yes" in capsys.readouterr().err

    def test_yes_skips_the_question(self, run, prompts):
        run.outcomes = [0, (0, "7\n"), 0]
        assert deploy.main(["--cloud", "--yes"]) == 0
        assert prompts.asked == []

    def test_the_question_says_what_will_happen(self, run, prompts, capsys):
        prompts.lines = ["no"]
        deploy.main(["--cloud"])
        assert "deploy-dev" in capsys.readouterr().err


class TestCloud:
    def test_starts_waits_and_watches_the_run(self, run, sleeps, capsys):
        run.outcomes = [0, (0, "123\n"), 0]
        assert deploy.main(["--cloud", "--yes"]) == 0
        assert run.calls == [
            ["gh", "workflow", "run", "deploy-dev.yml", "--ref", "develop"],
            LIST_CMD,
            ["gh", "run", "watch", "123", "--exit-status"],
        ]
        assert sleeps == [5]
        assert "123" in capsys.readouterr().out

    def test_the_watch_status_is_returned(self, run):
        run.outcomes = [0, (0, "9\n"), 1]
        assert deploy.main(["--cloud", "--yes"]) == 1

    def test_a_failed_start_stops_before_looking_for_a_run(self, run, sleeps, capsys):
        run.outcomes = [1]
        assert deploy.main(["--cloud", "--yes"]) == 1
        assert len(run.calls) == 1
        assert sleeps == []
        assert "did not start the workflow" in capsys.readouterr().err

    def test_a_run_that_cannot_be_listed_stops(self, run, capsys):
        run.outcomes = [0, (1, "")]
        assert deploy.main(["--cloud", "--yes"]) == 1
        assert len(run.calls) == 2
        assert "Actions tab" in capsys.readouterr().err

    def test_a_null_run_id_stops(self, run):
        run.outcomes = [0, (0, "null\n")]
        assert deploy.main(["--cloud", "--yes"]) == 1
        assert len(run.calls) == 2

    def test_a_missing_gh_gets_a_clear_message(self, run, capsys):
        run.outcomes = [FileNotFoundError()]
        assert deploy.main(["--cloud", "--yes"]) == 1
        assert "GitHub CLI (gh) is not installed" in capsys.readouterr().err

    def test_a_missing_gh_while_watching_is_reported_too(self, run, capsys):
        run.outcomes = [0, (0, "9\n"), FileNotFoundError()]
        assert deploy.main(["--cloud", "--yes"]) == 1
        assert "GitHub CLI (gh) is not installed" in capsys.readouterr().err


class TestParseSettingsFile:
    def test_only_the_two_settings_are_kept(self):
        text = f"# a comment\n\nLINEUP_SELFHOST_SSH={SSH}\nOTHER=1\nnot a pair\nLINEUP_SELFHOST_DIR={DIR}\n"
        assert deploy.parse_env_file(text) == {
            "LINEUP_SELFHOST_SSH": SSH,
            "LINEUP_SELFHOST_DIR": DIR,
        }

    def test_matching_quotes_are_removed(self):
        text = "LINEUP_SELFHOST_DIR='/srv/a b'\nLINEUP_SELFHOST_SSH=\"lineup@lineup.example.com\"\n"
        assert deploy.parse_env_file(text) == {
            "LINEUP_SELFHOST_DIR": "/srv/a b",
            "LINEUP_SELFHOST_SSH": SSH,
        }

    def test_values_are_data_and_never_run(self, tmp_path):
        marker = tmp_path / "marker"
        text = f"LINEUP_SELFHOST_DIR=$(touch {marker})\n"
        assert deploy.parse_env_file(text) == {
            "LINEUP_SELFHOST_DIR": f"$(touch {marker})"
        }
        assert not marker.exists()


class TestLocalSettings:
    def test_the_environment_wins_and_the_file_is_not_read(self, home):
        write_settings("this is not even mode 600\n", mode=0o644)
        settings = deploy.local_settings(
            {"LINEUP_SELFHOST_SSH": SSH, "LINEUP_SELFHOST_DIR": DIR},
            deploy.settings_file(),
        )
        assert settings == (SSH, DIR)

    def test_the_file_is_used_when_the_environment_is_empty(self):
        write_settings(
            f"# comment\nOTHER=1\nLINEUP_SELFHOST_SSH={SSH}\nLINEUP_SELFHOST_DIR={DIR}\n"
        )
        assert deploy.local_settings({}, deploy.settings_file()) == (SSH, DIR)

    def test_the_environment_fills_one_setting_and_the_file_the_other(self):
        write_settings(f"LINEUP_SELFHOST_DIR={DIR}\n")
        settings = deploy.local_settings(
            {"LINEUP_SELFHOST_SSH": SSH}, deploy.settings_file()
        )
        assert settings == (SSH, DIR)

    def test_a_file_that_is_not_mode_600_is_refused_and_not_printed(self):
        write_settings(
            f"LINEUP_SELFHOST_SSH={SSH}\nLINEUP_SELFHOST_DIR={DIR}\n", mode=0o644
        )
        with pytest.raises(deploy.SettingsError, match="chmod 600") as refused:
            deploy.local_settings({}, deploy.settings_file())
        assert SSH not in str(refused.value)
        assert DIR not in str(refused.value)

    def test_missing_values_point_at_the_plan(self):
        with pytest.raises(deploy.SettingsError, match="M2") as refused:
            deploy.local_settings({}, deploy.settings_file())
        assert "LINEUP_SELFHOST_SSH" in str(refused.value)
        assert "./lineup.sh update" in str(refused.value)

    def test_a_target_starting_with_a_dash_is_refused_from_the_environment(self):
        with pytest.raises(deploy.SettingsError) as refused:
            deploy.local_settings(
                {"LINEUP_SELFHOST_SSH": "-oProxyCommand=x", "LINEUP_SELFHOST_DIR": DIR},
                deploy.settings_file(),
            )
        assert "oProxyCommand" not in str(refused.value)

    def test_a_target_starting_with_a_dash_is_refused_from_the_file(self):
        write_settings(
            f"LINEUP_SELFHOST_SSH=-oProxyCommand=x\nLINEUP_SELFHOST_DIR={DIR}\n"
        )
        with pytest.raises(deploy.SettingsError) as refused:
            deploy.local_settings({}, deploy.settings_file())
        assert "oProxyCommand" not in str(refused.value)

    def test_the_settings_file_lives_under_the_home_folder(self, home):
        assert deploy.settings_file() == home / ".config" / "lineup" / "selfhost.env"


class TestLocalRun:
    def test_runs_the_update_over_ssh_as_an_argument_list(
        self, run, monkeypatch, capsys
    ):
        set_local_env(monkeypatch)
        assert deploy.main(["--local", "--yes"]) == 0
        assert run.calls == [["ssh", "--", SSH, "cd /srv/lineup && ./lineup.sh update"]]
        output = capsys.readouterr()
        assert SSH not in output.out + output.err
        assert DIR not in output.out + output.err

    def test_the_version_is_passed_through(self, run, monkeypatch):
        set_local_env(monkeypatch)
        assert deploy.main(["--local", "--version", "v1.2.3", "--yes"]) == 0
        assert (
            run.calls[0][-1] == "cd /srv/lineup && ./lineup.sh update --version v1.2.3"
        )

    def test_the_directory_is_quoted_for_the_remote_shell(self, run, monkeypatch):
        set_local_env(monkeypatch, directory="/srv/my lineup; rm -rf ~")
        assert deploy.main(["--local", "--yes"]) == 0
        assert run.calls[0][-1] == "cd '/srv/my lineup; rm -rf ~' && ./lineup.sh update"

    def test_the_ssh_status_is_returned(self, run, monkeypatch, capsys):
        set_local_env(monkeypatch)
        run.outcomes = [255]
        assert deploy.main(["--local", "--yes"]) == 255
        assert "did not finish" in capsys.readouterr().err

    def test_a_missing_ssh_is_reported(self, run, monkeypatch, capsys):
        set_local_env(monkeypatch)
        run.outcomes = [FileNotFoundError()]
        assert deploy.main(["--local", "--yes"]) == 1
        assert "ssh is not installed" in capsys.readouterr().err

    def test_a_refused_target_runs_nothing_and_prints_nothing_of_it(
        self, run, monkeypatch, capsys
    ):
        set_local_env(monkeypatch, ssh="-oProxyCommand=x")
        assert deploy.main(["--local", "--yes"]) == 1
        assert run.calls == []
        output = capsys.readouterr()
        assert "ProxyCommand=x" not in output.out + output.err

    def test_a_non_private_file_runs_nothing(self, run, capsys):
        write_settings(
            f"LINEUP_SELFHOST_SSH={SSH}\nLINEUP_SELFHOST_DIR={DIR}\n", mode=0o640
        )
        assert deploy.main(["--local", "--yes"]) == 1
        assert run.calls == []
        output = capsys.readouterr()
        assert SSH not in output.out + output.err

    def test_missing_settings_run_nothing_and_ask_nothing(self, run, prompts):
        assert deploy.main(["--local"]) == 1
        assert run.calls == []
        assert prompts.asked == []

    def test_the_question_names_the_action_but_not_the_settings(
        self, run, prompts, monkeypatch, capsys
    ):
        set_local_env(monkeypatch)
        prompts.lines = ["yes"]
        run.outcomes = [0]
        assert deploy.main(["--local"]) == 0
        output = capsys.readouterr()
        assert "backup first" in output.err
        assert "newest release" in output.err
        assert SSH not in output.err
        assert DIR not in output.err

    def test_a_chosen_version_is_named_in_the_question(
        self, run, prompts, monkeypatch, capsys
    ):
        set_local_env(monkeypatch)
        prompts.lines = ["yes"]
        assert deploy.main(["--local", "--version", "v2.0.0"]) == 0
        assert "v2.0.0" in capsys.readouterr().err

    def test_declining_runs_nothing(self, run, prompts, monkeypatch, capsys):
        set_local_env(monkeypatch)
        prompts.lines = ["n"]
        assert deploy.main(["--local"]) == 1
        assert run.calls == []
        assert "Aborted: nothing was changed." in capsys.readouterr().err


def test_the_script_never_uses_a_shell():
    """A shell would let a value from the settings file run as code, so no call may pass shell=True."""
    tree = ast.parse(SCRIPT.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "shell":
            assert not (
                isinstance(node.value, ast.Constant) and node.value.value is True
            )


def test_run_as_a_program_without_a_target_exits_2(monkeypatch, run):
    """The `__main__` guard: `task deploy < /dev/null` must stop with the usage code and run nothing."""
    monkeypatch.setattr(sys, "argv", ["deploy.py"])
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exited.value.code == 2
    assert run.calls == []
