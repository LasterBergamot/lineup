import importlib
from unittest.mock import patch

import app as app_module


def test_sentry_not_initialized_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with patch("sentry_sdk.init") as mock_init:
        importlib.reload(app_module)
    mock_init.assert_not_called()


def test_sentry_initialized_with_dsn(monkeypatch):
    dsn = "https://public@o0.ingest.sentry.io/0"
    monkeypatch.setenv("SENTRY_DSN", dsn)
    with patch("sentry_sdk.init") as mock_init:
        importlib.reload(app_module)
    mock_init.assert_called_once_with(dsn=dsn, traces_sample_rate=0.0)


def teardown_module(module):
    import os

    os.environ.pop("SENTRY_DSN", None)
    with patch("sentry_sdk.init"):
        importlib.reload(app_module)
