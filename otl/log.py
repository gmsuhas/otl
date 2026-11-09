"""A small event log, closer to beam-telemetry than to a trace.

Each line is one event:

    12:01:02.100 web request start path=/
    12:01:02.180 web request stop  status=200

The clock is the time of day. The name is the words before the phase
(`start`, `stop`, `event`, or `fail`). Whatever remains is `key=value`
attributes. A name with no phase is a point event.
"""

from __future__ import annotations

PHASES = ("start", "stop", "event", "fail")


class LogError(ValueError):
    """A line could not be read as an event."""


class Event:
    def __init__(self, clock_ms, name, phase, attributes, line_no):
        self.clock_ms = clock_ms
        self.name = name
        self.phase = phase
        self.attributes = attributes
        self.line_no = line_no

    def __repr__(self):
        return "Event(%r, %r, %r)" % (self.name, self.phase, self.clock_ms)


def parse_clock(text):
    """Turn `HH:MM:SS` or `HH:MM:SS.mmm` into milliseconds since midnight."""
    clock, dot, fraction = text.partition(".")
    parts = clock.split(":")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise LogError("expected a clock like 12:01:02.100, got %r" % text)
    hours, minutes, seconds = (int(part) for part in parts)
    if hours > 23 or minutes > 59 or seconds > 59:
        raise LogError("clock %r is not a time of day" % text)
    millis = 0
    if dot:
        if not fraction.isdigit() or not 1 <= len(fraction) <= 3:
            raise LogError("expected 1 to 3 digits after the clock, got %r" % text)
        millis = int(fraction) * (10 ** (3 - len(fraction)))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def parse_attributes(words):
    attributes = {}
    for word in words:
        key, equals, value = word.partition("=")
        if not equals or not key:
            raise LogError("expected key=value, got %r" % word)
        attributes[key] = _coerce(value)
    return attributes


def _coerce(value):
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    try:
        number = float(value)
    except ValueError:
        return value
    if value.lower() in ("nan", "inf", "-inf", "+inf"):
        return value
    return number


def parse_line(line, line_no):
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    words = text.split()
    if len(words) < 2:
        raise LogError("line %d needs a clock and a name" % line_no)
    try:
        clock_ms = parse_clock(words[0])
    except LogError as error:
        raise LogError("line %d: %s" % (line_no, error)) from None

    body = words[1:]
    phase_at = [
        index
        for index, word in enumerate(body)
        if word in PHASES and "=" not in word
    ]
    if len(phase_at) > 1:
        raise LogError("line %d has two phases" % line_no)
    if not phase_at:
        phase = "event"
        name_and_attrs = body
    elif phase_at[0] == len(body) - 1:
        phase = body[-1]
        name_and_attrs = body[:-1]
    else:
        phase = body[phase_at[0]]
        name_words = body[: phase_at[0]]
        attribute_words = body[phase_at[0] + 1 :]
        if not name_words:
            raise LogError("line %d has no event name" % line_no)
        if any("=" not in word for word in attribute_words):
            raise LogError(
                "line %d: words after the phase must be key=value" % line_no
            )
        try:
            attributes = parse_attributes(attribute_words)
        except LogError as error:
            raise LogError("line %d: %s" % (line_no, error)) from None
        return Event(clock_ms, " ".join(name_words), phase, attributes, line_no)
    attributes_at = next(
        (index for index, word in enumerate(name_and_attrs) if "=" in word),
        len(name_and_attrs),
    )
    name_words = name_and_attrs[:attributes_at]
    attribute_words = name_and_attrs[attributes_at:]
    if not name_words:
        raise LogError("line %d has no event name" % line_no)
    if any("=" not in word for word in attribute_words):
        raise LogError(
            "line %d: words after the name must be key=value" % line_no
        )
    try:
        attributes = parse_attributes(attribute_words)
    except LogError as error:
        raise LogError("line %d: %s" % (line_no, error)) from None
    return Event(clock_ms, " ".join(name_words), phase, attributes, line_no)


def parse_log(text):
    events = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        event = parse_line(line, line_no)
        if event is not None:
            events.append(event)
    events.sort(key=lambda event: (event.clock_ms, event.line_no))
    return events
