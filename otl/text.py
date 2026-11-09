"""Render a trace as indented text, so you can read it without a collector."""

from __future__ import annotations


def render(roots):
    lines = []
    for span in roots:
        _render(span, 0, lines)
    return "\n".join(lines) + ("\n" if lines else "")


def _render(span, depth, lines):
    indent = "  " * depth
    clock = _clock(span.start_ms)
    if span.end_ms is None:
        timing = "unclosed"
    else:
        timing = "%dms" % (span.end_ms - span.start_ms)
    mark = ""
    if span.status_code == 2:
        mark = " FAIL"
        if span.status_message:
            mark += " " + span.status_message
    lines.append("%s%s  %s  %s%s" % (indent, clock, span.name, timing, mark))
    for event in span.events:
        extra = ""
        if event.attributes:
            extra = "  " + " ".join(
                "%s=%s" % (key, event.attributes[key]) for key in event.attributes
            )
        lines.append(
            "%s  %s  . %s%s" % (indent, _clock(event.clock_ms), event.name, extra)
        )
    for child in span.children:
        _render(child, depth + 1, lines)


def _clock(millis):
    seconds, ms = divmod(millis, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return "%02d:%02d:%02d.%03d" % (hours, minutes, seconds, ms)
