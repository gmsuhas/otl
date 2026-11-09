"""Write one trace as OTLP JSON.

This is the JSON mapping from the OTLP spec, not a client and not a
collector. Trace and span ids are hex. Span kind and status are integers.
Timestamps are decimal strings of nanoseconds, because the spec encodes
64-bit fields that way.

https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding
"""

from __future__ import annotations

import datetime
import json
import secrets

from otl.trace import walk

_NS_PER_MS = 1_000_000


def new_trace_id():
    return secrets.token_hex(16)


def new_span_id():
    return secrets.token_hex(8)


def export_request(roots, service_name, trace_id=None, ids=None, day=None):
    """Build an ExportTraceServiceRequest as plain data.

    `day` is a datetime.date. The clocks in the log are times of day, so the
    export adds them to midnight UTC of that date. Without it, the spans would
    sit at the unix epoch.
    """
    chosen = ids if ids is not None else _Ids()
    trace = trace_id or new_trace_id()
    origin_ms = _midnight_utc_ms(day)
    spans = []
    for span in walk(roots):
        span_id = chosen.span_id(span)
        parent = chosen.span_id(span.parent) if span.parent is not None else None
        body = {
            "traceId": trace,
            "spanId": span_id,
            "name": span.name,
            "kind": 1,
            "startTimeUnixNano": _nano(origin_ms + span.start_ms),
            "attributes": _attributes(span.attributes),
            "events": [_event(event, origin_ms) for event in span.events],
            "status": {"code": span.status_code},
        }
        if parent is not None:
            body["parentSpanId"] = parent
        if span.end_ms is not None:
            body["endTimeUnixNano"] = _nano(origin_ms + span.end_ms)
        if span.status_message:
            body["status"]["message"] = span.status_message
        spans.append(body)
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": _attributes({"service.name": service_name})
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "otl"},
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def dumps(request):
    return json.dumps(request, indent=2, ensure_ascii=False) + "\n"


def _midnight_utc_ms(day):
    if day is None:
        day = datetime.datetime.now(datetime.timezone.utc).date()
    if isinstance(day, datetime.datetime):
        day = day.date()
    midnight = datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc)
    return int(midnight.timestamp() * 1000)


def _nano(clock_ms):
    return str(clock_ms * _NS_PER_MS)


def _attributes(mapping):
    return [{"key": key, "value": _value(mapping[key])} for key in mapping]


def _value(value):
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}


def _event(event, origin_ms):
    body = {
        "timeUnixNano": _nano(origin_ms + event.clock_ms),
        "name": event.name,
        "attributes": _attributes(event.attributes),
    }
    return body


class _Ids:
    """Stable ids for one export. Tests pass their own."""

    def __init__(self):
        self._ids = {}

    def span_id(self, span):
        key = id(span)
        if key not in self._ids:
            self._ids[key] = new_span_id()
        return self._ids[key]
