"""Portable acceptance for isolated yabai native-controller contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts import phase3_native_control_bridge as bridge
from scripts.phase3_native_auto_entry import command
from scripts.phase3_native_yabai_automation import NativeController, _action, _state_matches, _window_matches

pytestmark = pytest.mark.medium


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Set Kitty to a DARK color theme. Then click Continue", "dark"),
        ("Change the SAME Kitty window's actual foreground/background to a LIGHT color theme", "light"),
        ("Shrink Kitty below 790 physical px wide", "shrink"),
        ("Make Kitty shorter or narrower until page capacity changes", "shrink"),
        ("Resize the Kitty window. For a capacity transition, reduce HEIGHT", "shrink"),
        ("Expand Kitty toward its original width", "expand"),
        ("Enlarge Kitty to at least 950 physical pixels", "initial"),
        ("Use any normally sized Kitty window", "initial"),
        ("Click Continue, then focus Kitty and type n followed by Enter.", "n"),
        ("Click Continue, then focus Kitty and type p followed by Enter.", "p"),
        ("Click Continue, focus Kitty and press Enter on a BLANK input line", "enter"),
    ],
)
def test_all_native_dialog_actions_are_explicit(prompt: str, expected: str) -> None:
    assert _action(prompt) == expected


def test_unknown_dialog_is_not_silently_approved() -> None:
    with pytest.raises(ValueError, match="Unrecognized native GUI"):
        _action("Rearrange your unrelated desktop windows")


@pytest.mark.parametrize(
    ("state", "layout", "floating", "expected"),
    [
        ("unmanaged", "bsp", True, True),
        ("floating", "bsp", True, True),
        ("bsp", "bsp", False, True),
        ("float-space", "float", True, True),
        ("bsp", "bsp", True, False),
        ("unmanaged", "bsp", False, False),
        ("float-space", "bsp", True, False),
        ("floating", "float", True, False),
    ],
)
def test_management_mode_requires_observed_yabai_state(
    state: str, layout: str, floating: bool, expected: bool
) -> None:
    assert _state_matches({"is-floating": floating}, {"type": layout}, state) is expected


def test_controller_never_uses_focus_or_app_name_as_window_identity(tmp_path: Path) -> None:
    controller = NativeController(root=tmp_path, state="floating", case="resize", height=2)
    title = controller.title
    assert _window_matches({"app": "kitty", "title": title}, title)
    assert not _window_matches({"app": "kitty", "title": title + "-other"}, title)
    assert not _window_matches({"app": "Firefox", "title": title}, title)


def test_controller_rejects_unrelated_windows_on_test_space(tmp_path: Path, monkeypatch) -> None:
    controller = NativeController(root=tmp_path, state="bsp", case="lifecycle", height=2)
    controller.space_index = 5
    controller.window_id = 100
    window = {"id": 100, "title": controller.title, "app": "kitty", "space": 5, "is-floating": False}
    unrelated = {"id": 101, "title": "Unrelated", "app": "Other", "space": 5}
    def fake_query(*args: str):
        if args[:2] == ("--windows", "--window"):
            return window
        if args[:2] == ("--spaces", "--space"):
            return {"index": 5, "type": "bsp"}
        return [window, unrelated]
    monkeypatch.setattr(controller, "query", fake_query)
    with pytest.raises(RuntimeError, match="unrelated window"):
        controller._verify()


def test_bridge_uses_atomic_events_and_bounded_ack(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "events").mkdir()
    (tmp_path / "acks").mkdir()
    monkeypatch.setenv("WSKR_NATIVE_CONTROL_DIR", str(tmp_path))
    def controller_tick(_delay: float) -> None:
        for event_path in (tmp_path / "events").glob("*.json"):
            event = json.loads(event_path.read_text(encoding="utf-8"))
            (tmp_path / "acks" / f"{event['id']}.json").write_text(
                json.dumps({"ok": True, "ack": event["action"]}), encoding="utf-8"
            )
    monkeypatch.setattr(bridge.time, "sleep", controller_tick)
    reply = bridge.request("ready", case="resize")
    assert reply["ack"] == "ready"
    assert list((tmp_path / "acks").iterdir()) == []


def test_foreground_worker_commands_keep_existing_acceptance_gates() -> None:
    for case in ("resize", "paging", "lifecycle", "appearance"):
        argv = command(case, 6, "yabai")
        assert argv[:2] == [sys.executable, "-m"]
        assert argv[2] == f"scripts.phase3_native_macos_{case}"
        assert argv[3:5] == ["--mode", "yabai"]
        if case == "resize":
            assert argv[-3:] == ["--height", "6", "--clean-scrollback"]
        if case == "paging":
            assert argv[-1] == "--require-capacity-change"


def test_distinct_kitty_and_yabai_window_ids_are_never_confused(tmp_path: Path, monkeypatch) -> None:
    controller = NativeController(root=tmp_path, state="floating", case="paging", height=2)
    controller.window_id = 407
    controller.socket_path = tmp_path / "unused.sock"
    commands: list[tuple[str, ...]] = []

    def fake_kitty(*args: str) -> str:
        commands.append(args)
        return json.dumps([{"tabs": [{"windows": [{"id": 19, "title": "child-changeable-title"}]}]}])

    monkeypatch.setattr(controller, "kitty", fake_kitty)
    controller._identify_kitty_window()
    assert controller.window_id == 407
    assert controller.kitty_window_id == 19
    assert controller._target() == "id:19"
    assert commands == [("ls",)]


def test_ambiguous_kitty_internal_windows_cannot_receive_input(tmp_path: Path, monkeypatch) -> None:
    controller = NativeController(root=tmp_path, state="bsp", case="paging", height=2)
    monkeypatch.setattr(
        controller,
        "kitty",
        lambda *_args: json.dumps(
            [{"tabs": [{"windows": [{"id": 19}, {"id": 20}]}]}]
        ),
    )
    with pytest.raises(RuntimeError, match="exactly one Kitty-internal"):
        controller._identify_kitty_window(timeout=0.01)
    with pytest.raises(RuntimeError, match="not established"):
        controller._target()
