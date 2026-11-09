"""Turn events into one trace, shaped like an OTLP ExportTraceServiceRequest.

A `start` opens a span. A later `stop` or `fail` with the same name closes
the most recently opened one, so two requests with the same name stay nested
correctly. A span that never closes is recorded with the attributes it had
and no end time. A point `event` lands on the open span of that name, or on
the span that is open around it.
"""

from __future__ import annotations

SPAN_KIND_INTERNAL = 1

STATUS_UNSET = 0
STATUS_OK = 1
STATUS_ERROR = 2


class Span:
    def __init__(self, name, start_ms, attributes):
        self.name = name
        self.start_ms = start_ms
        self.end_ms = None
        self.attributes = dict(attributes)
        self.events = []
        self.status_code = STATUS_UNSET
        self.status_message = ""
        self.children = []
        self.parent = None

    @property
    def closed(self):
        return self.end_ms is not None


def build_trace(events):
    """Return the root spans. Children hang off their parent."""
    roots = []
    open_spans = []
    for event in events:
        if event.phase == "start":
            span = Span(event.name, event.clock_ms, event.attributes)
            if open_spans:
                span.parent = open_spans[-1]
                open_spans[-1].children.append(span)
            else:
                roots.append(span)
            open_spans.append(span)
            continue

        if event.phase in ("stop", "fail"):
            span = _take_open(open_spans, event.name)
            if span is None:
                span = Span(event.name, event.clock_ms, {})
                _attach(span, open_spans, roots)
            span.end_ms = event.clock_ms
            span.attributes.update(event.attributes)
            if event.phase == "fail":
                span.status_code = STATUS_ERROR
                message = event.attributes.get("error")
                if message is not None:
                    span.status_message = str(message)
            elif span.status_code == STATUS_UNSET:
                span.status_code = STATUS_OK
            continue

        span = _find_open(open_spans, event.name) or (
            open_spans[-1] if open_spans else None
        )
        if span is None:
            span = Span(event.name, event.clock_ms, {})
            span.end_ms = event.clock_ms
            span.status_code = STATUS_OK
            roots.append(span)
        span.events.append(event)
    return roots


def _find_open(open_spans, name):
    for span in reversed(open_spans):
        if span.name == name:
            return span
    return None


def _take_open(open_spans, name):
    for index in range(len(open_spans) - 1, -1, -1):
        if open_spans[index].name == name:
            return open_spans.pop(index)
    return None


def _attach(span, open_spans, roots):
    if open_spans:
        span.parent = open_spans[-1]
        open_spans[-1].children.append(span)
    else:
        roots.append(span)


def walk(spans):
    """Yield spans in the order they opened."""
    for span in spans:
        yield span
        yield from walk(span.children)
