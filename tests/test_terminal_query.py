"""Safe OSC I/O tests, including a real pseudo-terminal round trip."""

import os
import pty
import termios
import threading

import pytest

from wskr.terminal import query


def _assert_restored_terminal_settings(slave: int, before: list) -> None:
    """Check user-managed termios state; macOS owns the EXTPROC flag."""
    after = termios.tcgetattr(slave)
    assert after[:3] == before[:3]
    assert after[4:] == before[4:]
    kernel_flags = getattr(termios, "EXTPROC", 0)
    assert after[3] & ~kernel_flags == before[3] & ~kernel_flags


@pytest.mark.small
def test_query_requires_explicit_input_ownership():
    with pytest.raises(query.TerminalQueryError, match="exclusive input"):
        query.query_osc(b"\x1b]11;?\x07")


@pytest.mark.small
def test_query_refuses_redirected_output(monkeypatch):
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: False)
    with pytest.raises(query.TerminalQueryError, match="output"):
        query.query_osc(b"\x1b]11;?\x07", owns_input=True, on_unmatched=lambda b: None)


@pytest.mark.small
def test_query_rejects_non_osc_requests(monkeypatch):
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: True)
    with pytest.raises(ValueError, match="OSC"):
        query.query_osc(b"\x1b[6n", owns_input=True, on_unmatched=lambda b: None)


@pytest.mark.small
def test_query_bounds_configuration(monkeypatch):
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: True)
    with pytest.raises(ValueError, match="timeout"):
        query.query_osc(b"\x1b]11;?\x07", owns_input=True, on_unmatched=lambda b: None, timeout=-2)


@pytest.mark.medium
def test_pty_reply_restores_termios_and_forwards_unrelated_input(monkeypatch):
    master, slave = pty.openpty()
    before = termios.tcgetattr(slave)
    unmatched = []
    monkeypatch.setattr(query, "_open_tty", lambda: os.dup(slave))
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: True)

    def responder():
        request = os.read(master, 100)
        assert request == b"\x1b]11;?\x07"
        os.write(master, b"a\x1b]10;rgb:ffff/ffff/ffff\x07\x1b]11;rgb:0000/0000/0000\x1b\\")

    thread = threading.Thread(target=responder, daemon=True)
    thread.start()
    try:
        response = query.query_osc(
            b"\x1b]11;?\x07",
            owns_input=True,
            on_unmatched=unmatched.append,
            timeout=1,
        )
        assert response == b"\x1b]11;rgb:0000/0000/0000\x1b\\"
        assert unmatched == [b"a\x1b]10;rgb:ffff/ffff/ffff\x07"]
        _assert_restored_terminal_settings(slave, before)
    finally:
        thread.join(timeout=2)
        os.close(master)
        os.close(slave)
    assert not thread.is_alive()


@pytest.mark.medium
def test_pty_timeout_restores_termios(monkeypatch):
    master, slave = pty.openpty()
    before = termios.tcgetattr(slave)
    monkeypatch.setattr(query, "_open_tty", lambda: os.dup(slave))
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: True)
    try:
        with pytest.raises(TimeoutError):
            query.query_osc(
                b"\x1b]11;?\x07",
                owns_input=True,
                on_unmatched=lambda b: None,
                timeout=0.025,
            )
        _assert_restored_terminal_settings(slave, before)
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.medium
def test_partial_reply_on_timeout_is_routed_to_owner(monkeypatch):
    master, slave = pty.openpty()
    unmatched = []
    monkeypatch.setattr(query, "_open_tty", lambda: os.dup(slave))
    monkeypatch.setattr(query, "_stdout_is_tty", lambda: True)

    def responder():
        os.read(master, 100)
        os.write(master, b"\x1b]11;rgb:12")

    thread = threading.Thread(target=responder, daemon=True)
    thread.start()
    try:
        with pytest.raises(TimeoutError):
            query.query_osc(
                b"\x1b]11;?\x07",
                owns_input=True,
                on_unmatched=unmatched.append,
                timeout=0.08,
            )
        assert unmatched == [b"\x1b]11;rgb:12"]
    finally:
        thread.join(timeout=2)
        os.close(master)
        os.close(slave)
