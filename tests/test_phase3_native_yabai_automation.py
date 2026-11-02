"""Portable acceptance for isolated yabai native-controller contracts."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

from scripts import phase3_native_control_bridge as bridge
from scripts.phase3_native_auto_entry import command
from scripts.phase3_native_yabai_automation import NativeController, _action, _state_matches, _window_matches

if TYPE_CHECKING:
    from pathlib import Path


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
    state: str, layout: str, *, floating: bool, expected: bool
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

    def fake_query(*args: str) -> dict:
        if args[:2] == ("--windows", "--window"):
            return window
        if args[:2] == ("--spaces", "--space"):
            return {"index": 5, "type": "bsp"}
        msg = f"Unexpected single-object query: {args!r}"
        raise AssertionError(msg)

    monkeypatch.setattr(controller, "query", fake_query)
    monkeypatch.setattr(controller, "query_list", lambda *_args: [window, unrelated])
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


def test_own_space_uses_action_then_selector_for_focus(tmp_path: Path, monkeypatch) -> None:
    controller = NativeController(root=tmp_path, state="bsp", case="resize", height=2)
    original = {"uuid": "previous", "index": 2}
    created = {"uuid": "new", "index": 3}
    calls: list[tuple[str, ...]] = []
    space_lists = iter(([original], [original, created]))
    monkeypatch.setattr(controller, "query", lambda *_args: original)
    monkeypatch.setattr(controller, "_spaces", lambda: next(space_lists))
    monkeypatch.setattr(controller, "yabai", lambda *args: calls.append(args) or "")
    controller._own_space()
    assert controller.space_uuid == "new"
    assert calls == [
        ("space", "--create"),
        ("space", "3", "--label", controller.space_label),
        ("space", controller.space_label, "--layout", "bsp"),
        ("space", "--focus", controller.space_label),
    ]


def test_cleanup_uses_action_then_selector_for_exact_owned_space(tmp_path: Path, monkeypatch) -> None:
    controller = NativeController(root=tmp_path, state="floating", case="lifecycle", height=2)
    controller.previous_uuid = "original"
    controller.space_uuid = "owned"
    spaces = [
        {"uuid": "original", "index": 2},
        {"uuid": "owned", "index": 5},
        {"uuid": "unrelated", "index": 6},
    ]
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(controller, "_spaces", lambda: spaces)
    monkeypatch.setattr(controller, "query_list", lambda *_args: [])
    monkeypatch.setattr(controller, "yabai", lambda *args: calls.append(args) or "")
    controller._restore_previous_space()
    controller._destroy_owned_space()
    assert calls == [("space", "--focus", "2"), ("space", "--destroy", "5")]
    assert controller.cleanup_errors == []


def test_cleanup_preserves_owned_space_if_another_window_moves_there(tmp_path: Path, monkeypatch) -> None:
    controller = NativeController(root=tmp_path, state="bsp", case="paging", height=2)
    controller.space_uuid = "owned"
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(controller, "_spaces", lambda: [{"uuid": "owned", "index": 5}])
    monkeypatch.setattr(controller, "query_list", lambda *_args: [{"id": 990, "space": 5}])
    monkeypatch.setattr(controller, "yabai", lambda *args: calls.append(args) or "")
    controller._destroy_owned_space()
    assert calls == []
    assert "still contains windows" in controller.cleanup_errors[0]


def test_window_lookup_uses_full_snapshot_after_yabai_selector_rejects_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = NativeController(root=tmp_path, state="unmanaged", case="resize", height=2)
    controller.window_id = 7225
    controller.window_owner_pid = 2205
    controller.space_index = 3
    state = {
        "id": 7225,
        "pid": 2205,
        "app": "kitty",
        "title": "zsh changed the tab title",
        "space": 3,
        "is-floating": True,
    }
    monkeypatch.setattr(controller, "query_list", lambda *_args: [state])
    def forbid_window_query(*args: str) -> dict:
        msg = f"Targeted yabai query must not be used: {args!r}"
        raise AssertionError(msg)

    monkeypatch.setattr(controller, "query", forbid_window_query)
    assert controller._window() == state


def test_window_disappearance_fails_with_candidate_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = NativeController(root=tmp_path, state="bsp", case="resize", height=2)
    controller.window_id = 7225
    controller.space_index = 3
    unrelated = {"id": 991, "app": "kitty", "title": "unrelated", "pid": 9001, "space": 2}
    monkeypatch.setattr(controller, "query_list", lambda *_args: [unrelated])
    with pytest.raises(RuntimeError, match="disappeared or became ambiguous"):
        controller._window()
    assert controller.window_observations[-1]["missing_id"] == 7225
    assert controller.window_observations[-1]["kitty_candidates"][0]["id"] == 991


def test_window_id_reuse_rejected_even_if_application_and_space_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = NativeController(root=tmp_path, state="unmanaged", case="resize", height=2)
    controller.window_id = 7225
    controller.window_owner_pid = 2205
    controller.space_index = 3
    other = {"id": 7225, "pid": 9001, "app": "kitty", "space": 3}
    monkeypatch.setattr(controller, "query_list", lambda *_args: [other])
    with pytest.raises(RuntimeError, match="PID changed"):
        controller._window()


def test_spawn_waits_for_two_accessibility_ready_snapshots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = NativeController(root=tmp_path, state="unmanaged", case="resize", height=2)
    controller.space_index = 3
    raw = {
        "id": 7225,
        "pid": 2205,
        "app": "kitty",
        "title": controller.title,
        "space": 3,
        "is-floating": True,
        "has-ax-reference": False,
    }
    observed: list[bool] = []
    snapshots = iter([False, True, True])

    def fake_windows(*args: str) -> list[dict]:
        assert args == ("--windows",)
        raw["has-ax-reference"] = next(snapshots, True)
        observed.append(raw["has-ax-reference"])
        return [dict(raw)]

    class FakeProcess:
        pid = 4444

        def poll(self) -> None:
            return None

    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(controller, "query_list", fake_windows)
    monkeypatch.setattr(controller, "query", lambda *_args: {"type": "bsp", "index": 3})
    monkeypatch.setattr(controller, "yabai", lambda *args: commands.append(args) or "")
    monkeypatch.setattr(controller, "_identify_kitty_window", lambda: None)
    monkeypatch.setattr(
        "scripts.phase3_native_yabai_automation.subprocess.Popen", lambda *_a, **_kw: FakeProcess()
    )
    try:
        controller._spawn()
    finally:
        controller._remove_socket()
    assert controller.window_id == 7225
    assert controller.window_owner_pid == 2205
    assert observed[:3] == [False, True, True]
    assert ("rule", "--remove", controller.rule_label) in commands
