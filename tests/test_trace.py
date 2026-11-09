import unittest

from otl.log import parse_log
from otl.otlp import export_request
from otl.text import render
from otl.trace import STATUS_ERROR, STATUS_OK, build_trace, walk


REQUEST = """\
12:01:02.100 web request start method=GET path=/
12:01:02.110 db query start table=users
12:01:02.140 db query event rows=1
12:01:02.160 db query stop
12:01:02.190 web request stop status=200
"""


class TraceTests(unittest.TestCase):
    def test_stop_closes_the_matching_span(self):
        roots = build_trace(parse_log(REQUEST))
        self.assertEqual(len(roots), 1)
        root = roots[0]
        self.assertEqual(root.name, "web request")
        self.assertEqual(root.end_ms - root.start_ms, 90)
        self.assertEqual(root.status_code, STATUS_OK)
        self.assertEqual(root.attributes["status"], 200)
        child = root.children[0]
        self.assertEqual(child.name, "db query")
        self.assertEqual(child.end_ms - child.start_ms, 50)
        self.assertEqual(child.events[0].attributes["rows"], 1)

    def test_same_name_closes_the_inner_span(self):
        text = (
            "00:00:00.000 work start\n"
            "00:00:00.100 work start\n"
            "00:00:00.200 work stop\n"
            "00:00:00.300 work stop\n"
        )
        roots = build_trace(parse_log(text))
        outer, = roots
        inner, = outer.children
        self.assertEqual(inner.end_ms - inner.start_ms, 100)
        self.assertEqual(outer.end_ms - outer.start_ms, 300)

    def test_a_failure_marks_the_span(self):
        text = "09:15:00.020 pay start\n09:15:00.400 pay fail error=declined\n"
        span, = build_trace(parse_log(text))
        self.assertEqual(span.status_code, STATUS_ERROR)
        self.assertEqual(span.status_message, "declined")

    def test_an_unclosed_span_stays_open(self):
        text = "09:15:00.420 notify start channel=email\n"
        span, = build_trace(parse_log(text))
        self.assertIsNone(span.end_ms)
        self.assertEqual(span.attributes["channel"], "email")

    def test_a_stop_without_a_start_still_records(self):
        span, = build_trace(parse_log("00:00:01.000 orphan stop\n"))
        self.assertEqual(span.start_ms, span.end_ms)

    def test_text_shows_nesting_and_the_point_event(self):
        rendered = render(build_trace(parse_log(REQUEST)))
        self.assertIn("web request  90ms", rendered)
        self.assertIn("  db query  50ms", rendered)
        self.assertIn(". db query", rendered)
        self.assertIn("rows=1", rendered)

    def test_otlp_uses_hex_ids_integer_kind_and_string_nanos(self):
        class FixedIds:
            def span_id(self, span):
                return "aa" if span.parent is None else "bb"

        request = export_request(
            build_trace(parse_log(REQUEST)),
            "demo",
            trace_id="ab" * 16,
            ids=FixedIds(),
        )
        spans = request["resourceSpans"][0]["scopeSpans"][0]["spans"]
        self.assertEqual(spans[0]["traceId"], "ab" * 16)
        self.assertEqual(spans[0]["spanId"], "aa")
        self.assertEqual(spans[1]["parentSpanId"], "aa")
        self.assertEqual(spans[0]["kind"], 1)
        self.assertEqual(spans[0]["startTimeUnixNano"], "43262100000000")
        self.assertTrue(spans[0]["endTimeUnixNano"].isdigit())
        attributes = spans[0]["attributes"]
        self.assertEqual(attributes[0]["value"]["stringValue"], "GET")
        status = next(item for item in attributes if item["key"] == "status")
        self.assertEqual(status["value"]["intValue"], "200")
        resource = request["resourceSpans"][0]["resource"]["attributes"]
        self.assertEqual(resource[0]["key"], "service.name")


if __name__ == "__main__":
    unittest.main()
