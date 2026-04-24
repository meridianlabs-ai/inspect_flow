"""Tests for the _display module."""

import os

from inspect_flow._display.action import DisplayAction
from inspect_flow._display.display import (
    DisplayType,
    create_display,
    display,
    get_display_type,
    set_display,
    set_display_type,
)
from inspect_flow._display.full import FullDisplay
from inspect_flow._display.full_actions import (
    FullActionsDisplay,
    _BorderedTable,
    _OutputCapture,
    _SafeRenderable,
)
from inspect_flow._display.plain import PlainDisplay
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.measure import Measurement
from rich.table import Table


class TestPlainDisplay:
    def test_context_manager_sets_and_clears_global(self) -> None:
        with PlainDisplay() as d:
            assert display() is d
        assert display() is not d

    def test_update_action_prints_status_icons(
        self, recording_console: Console
    ) -> None:
        d = PlainDisplay()
        d.update_action("k", DisplayAction(description="Setup", status="pending"))
        d.update_action("k", DisplayAction(description="Setup", status="running"))
        d.update_action("k", DisplayAction(description="Setup", status="success"))
        d.update_action("k", DisplayAction(description="Setup", status="error"))
        output = recording_console.export_text()
        assert "[ ] Setup" in output
        assert "[..] Setup" in output
        assert "[OK] Setup" in output
        assert "[ERROR] Setup" in output

    def test_update_action_uses_key_when_no_description(
        self, recording_console: Console
    ) -> None:
        d = PlainDisplay()
        d.update_action("my-key", DisplayAction(status="pending"))
        assert "my-key" in recording_console.export_text()

    def test_update_action_with_info(self, recording_console: Console) -> None:
        d = PlainDisplay()
        d.update_action(
            "k", DisplayAction(description="Go", status="success", info="extra")
        )
        output = recording_console.export_text()
        assert "[OK] Go" in output
        assert "extra" in output

    def test_print_with_format_prefix(self, recording_console: Console) -> None:
        d = PlainDisplay()
        d.print("hello", action_key="a", format="success")
        d.print("world", action_key="a", format="error")
        d.print("plain", action_key="a")
        output = recording_console.export_text()
        assert "[OK] hello" in output
        assert "[ERROR] world" in output
        assert "plain" in output

    def test_print_blank_line_between_different_keys(
        self, recording_console: Console
    ) -> None:
        d = PlainDisplay()
        d.print("first", action_key="a")
        d.print("second", action_key="b")
        lines = recording_console.export_text().splitlines()
        # Expect: "first", blank, "second"
        assert lines[0].strip() == "first"
        assert lines[1].strip() == ""
        assert lines[2].strip() == "second"

    def test_title_get_set(self, recording_console: Console) -> None:
        d = PlainDisplay()
        assert d.get_title() is None
        d.set_title("My Flow")
        assert d.get_title() == ["My Flow"]
        assert "My Flow" in recording_console.export_text()

    def test_set_footer_is_noop(self) -> None:
        d = PlainDisplay()
        d.set_footer("anything")  # should not raise

    def test_stop_idempotent(self) -> None:
        with PlainDisplay():
            pass
        # Second stop (via __exit__) already happened; explicit stop should be safe
        d = PlainDisplay()
        d.stop()  # not started, should be a no-op


class TestDisplayFactory:
    _prev_display_type: DisplayType

    def setup_method(self) -> None:
        self._prev_display_type = get_display_type()
        set_display(None)

    def teardown_method(self) -> None:
        set_display(None)
        set_display_type(self._prev_display_type)

    def test_display_returns_plain_when_type_is_plain(self) -> None:
        set_display_type("plain")
        d = display()
        assert isinstance(d, PlainDisplay)

    def test_create_display_returns_plain_when_type_is_plain(self) -> None:
        set_display_type("plain")
        d = create_display(mode="run", actions={})
        assert isinstance(d, PlainDisplay)

    def test_create_display_returns_full_actions_when_type_is_full(self) -> None:
        set_display_type("full")
        d = create_display(mode="run", actions={})
        assert isinstance(d, FullActionsDisplay)


class TestFullDisplay:
    def test_context_manager_sets_and_clears_global(self) -> None:
        with FullDisplay() as d:
            assert display() is d
        assert display() is not d

    def test_set_title(self, recording_console: Console) -> None:
        d = FullDisplay()
        assert d.get_title() is None
        d.set_title("Run", "v2")
        assert d.get_title() == ["Run", "v2"]
        output = recording_console.export_text()
        assert "Run" in output
        assert "v2" in output

    def test_stop_clears_live_footer(self, recording_console: Console) -> None:
        d = FullDisplay()
        d._started = True
        set_display(d)
        d.set_footer("progress...")
        assert d._live is not None
        d.stop()
        assert d._live is None
        assert display() is not d


def _render_text(renderable: object, width: int = 60) -> str:
    """Render a Rich renderable to plain text."""
    c = Console(width=width, no_color=True, highlight=False)
    with c.capture() as capture:
        c.print(renderable)
    return capture.get()


class TestBorderedTable:
    def _make_table(self, *rows: str) -> Table:
        table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
        table.add_column(width=1)
        table.add_column()
        for row in rows:
            table.add_row("○", row)
        return table

    def test_no_title(self) -> None:
        bt = _BorderedTable(self._make_table("Setup"), mode="run")
        output = _render_text(bt)
        assert "╭" in output
        assert "╰" in output
        assert "Setup" in output
        # No title brackets should appear
        assert "[" not in output or "DRY RUN" not in output

    def test_with_title(self) -> None:
        bt = _BorderedTable(self._make_table("Setup"), mode="run", title=["My", "Flow"])
        output = _render_text(bt)
        assert "[My Flow]" in output

    def test_dry_run_markers(self) -> None:
        bt = _BorderedTable(self._make_table("Setup"), mode="dry_run")
        output = _render_text(bt)
        assert output.count("[DRY RUN]") == 4  # 2 top + 2 bottom

    def test_empty_messages_skipped(self) -> None:
        msgs: dict[str, list[RenderableType]] = {
            "a": ["msg-a"],
            "empty": [],
            "b": ["msg-b"],
        }
        bt = _BorderedTable(self._make_table("Setup"), mode="run", messages=msgs)
        output = _render_text(bt)
        assert "msg-a" in output
        assert "msg-b" in output

    def test_messages_with_separator(self) -> None:
        msgs: dict[str, list[RenderableType]] = {"a": ["msg-a"], "b": ["msg-b"]}
        bt = _BorderedTable(self._make_table("Setup"), mode="run", messages=msgs)
        output = _render_text(bt)
        assert "msg-a" in output
        assert "msg-b" in output

    def test_footer(self) -> None:
        bt = _BorderedTable(self._make_table("Setup"), mode="run", footer="my-footer")
        output = _render_text(bt)
        assert "my-footer" in output

    def test_height_with_console_output(self) -> None:
        bt = _BorderedTable(
            self._make_table("Setup"),
            mode="run",
            height=20,
            console_output=["line1", "line2"],
        )
        output = _render_text(bt)
        assert "line1" in output
        assert "line2" in output

    def test_rich_measure(self) -> None:
        bt = _BorderedTable(self._make_table("Setup"), mode="run")
        m = Measurement.get(Console(width=60), Console(width=60).options, bt)
        assert m.minimum > 0
        assert m.maximum >= m.minimum


class TestFullActionsDisplay:
    def test_update_action_adds_new_key(self) -> None:
        d = FullActionsDisplay(mode="run", actions={})
        d.update_action("new", DisplayAction(description="New task", status="pending"))
        assert "new" in d._actions
        assert d._actions["new"].description == "New task"

    def test_print_with_format_prefix(self) -> None:
        d = FullActionsDisplay(mode="run", actions={})
        d.print("hello", action_key="a", format="error")
        assert len(d._messages["a"]) == 1


class TestSafeRenderable:
    def test_catches_render_error(self) -> None:
        class _Bad:
            def __rich_console__(
                self, console: Console, options: ConsoleOptions
            ) -> RenderResult:
                raise RuntimeError("boom")

        output = _render_text(_SafeRenderable(_Bad()))
        assert "boom" in output


class TestOutputCapture:
    def test_captures_fd_writes(self) -> None:
        capture = _OutputCapture()
        capture.start()
        try:
            os.write(1, b"hello-capture")
        finally:
            result = capture.stop()
        assert b"hello-capture" in result
