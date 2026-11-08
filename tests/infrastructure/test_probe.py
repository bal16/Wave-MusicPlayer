"""Unit tests for infrastructure/probe.py."""

from __future__ import annotations

import subprocess

from infrastructure import probe


def test_probe_in_subprocess_true_on_clean_exit():
    assert probe.probe_in_subprocess("pass") is True


def test_probe_in_subprocess_false_on_failure():
    assert probe.probe_in_subprocess("raise SystemExit(1)") is False


def test_run_probe_returns_exit_code_and_stripped_stdout():
    assert probe.run_probe("print('3.0.20')") == (0, "3.0.20")


def test_run_probe_returns_nonzero_code():
    assert probe.run_probe("raise SystemExit(2)")[0] == 2


def test_run_probe_swallows_launch_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="python", timeout=1)

    monkeypatch.setattr(probe.subprocess, "run", boom)
    assert probe.run_probe("pass") == (1, "")


def test_run_probe_handles_missing_stdout(monkeypatch):
    class Result:
        returncode = 0
        stdout = None

    monkeypatch.setattr(probe.subprocess, "run", lambda *a, **k: Result())
    assert probe.run_probe("pass") == (0, "")


def test_probe_timeout_is_bounded():
    assert 0 < probe.PROBE_TIMEOUT_S <= 60
