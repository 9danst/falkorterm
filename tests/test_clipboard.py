from falkorterm.clipboard import (
    CLIPBOARD_MISSING_HINT,
    copy_text_system,
    format_copy_notification,
)


def test_copy_text_system_uses_first_available_tool(monkeypatch):
    calls: list[tuple[list[str], bytes]] = []

    monkeypatch.setattr(
        "falkorterm.clipboard.shutil.which",
        lambda name: "/usr/bin/wl-copy" if name == "wl-copy" else None,
    )

    def fake_run(cmd, input=None, check=False, timeout=None, capture_output=False):
        calls.append((list(cmd), input))
        return None

    monkeypatch.setattr("falkorterm.clipboard.subprocess.run", fake_run)
    assert copy_text_system("hello\nworld") is True
    assert calls == [(["wl-copy"], b"hello\nworld")]


def test_copy_text_system_returns_false_when_no_tools(monkeypatch):
    monkeypatch.setattr("falkorterm.clipboard.shutil.which", lambda _name: None)
    assert copy_text_system("x") is False


def test_copy_text_system_falls_back_to_pbcopy(monkeypatch):
    calls: list[tuple[list[str], bytes]] = []

    monkeypatch.setattr(
        "falkorterm.clipboard.shutil.which",
        lambda name: "/usr/bin/pbcopy" if name == "pbcopy" else None,
    )

    def fake_run(cmd, input=None, check=False, timeout=None, capture_output=False):
        calls.append((list(cmd), input))
        return None

    monkeypatch.setattr("falkorterm.clipboard.subprocess.run", fake_run)
    assert copy_text_system("mac") is True
    assert calls == [(["pbcopy"], b"mac")]


def test_format_copy_notification_success():
    assert format_copy_notification(True, "graph") == ("Copied graph", "information")


def test_format_copy_notification_failure_hints_clipboard_tools():
    message, severity = format_copy_notification(False, "graph")
    assert severity == "warning"
    assert "graph" in message
    assert CLIPBOARD_MISSING_HINT in message
