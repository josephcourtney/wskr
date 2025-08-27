import subprocess

import pytest

from wskr.tty.command import CommandRunner


def test_run_uses_default_timeout(monkeypatch):
    seen = {}

    def fake_run(cmd, *, timeout=None, **kwargs):
        seen["timeout"] = timeout
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    CommandRunner().run(["echo"])
    assert seen["timeout"] == 1.0


def test_check_output_returns_stdout(monkeypatch):
    def fake_run(cmd, *, timeout=None, capture_output=None, check=None, **kwargs):
        class P:
            stdout = "hi"

        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = CommandRunner().check_output(["echo"], text=True)
    assert out == "hi"


def test_run_retries(monkeypatch):
    calls = []

    def fake_run(cmd, *, timeout=None, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CommandRunner(retries=1)
    runner.run(["echo"])
    assert len(calls) == 2


def test_run_retry_exhausted(monkeypatch):
    def bad_run(cmd, *, timeout=None, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", bad_run)
    runner = CommandRunner(retries=1)
    with pytest.raises(subprocess.CalledProcessError):
        runner.run(["echo"])
