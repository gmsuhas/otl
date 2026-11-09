import datetime
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from otl.__main__ import main


class CliTests(unittest.TestCase):
    def test_otlp_places_the_span_on_the_given_day(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["otlp", "examples/request.log", "demo", "2026-11-08"])
        self.assertEqual(code, 0)
        body = json.loads(stdout.getvalue())
        start = int(
            body["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["startTimeUnixNano"]
        )
        expected = datetime.datetime(
            2026, 11, 8, 12, 1, 2, 100000, tzinfo=datetime.timezone.utc
        )
        self.assertEqual(start, int(expected.timestamp() * 1_000_000_000))
        self.assertEqual(
            body["resourceSpans"][0]["resource"]["attributes"][0]["value"]["stringValue"],
            "demo",
        )

    def test_a_bad_date_is_an_error(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["otlp", "examples/request.log", "2026-13-08"])
        self.assertEqual(code, 1)
        self.assertIn("2026-13-08", stderr.getvalue())

    def test_help_is_an_error_until_someone_asks_for_it_otherwise(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["--help"])
        self.assertEqual(code, 1)
        self.assertIn("YYYY-MM-DD", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
