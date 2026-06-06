from ngd.term_events import parse_terminal_events


def test_parses_mouse_and_focus():
    events = list(parse_terminal_events("[<35;93;23M\x1b[I"))
    assert [event.type for event in events] == ["mouse", "focus"]
