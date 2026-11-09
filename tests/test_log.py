import unittest

from otl.log import LogError, parse_clock, parse_line, parse_log


class ClockTests(unittest.TestCase):
    def test_millis_are_padded(self):
        self.assertEqual(
            parse_clock("09:15:00.4"), 9 * 3600 * 1000 + 15 * 60 * 1000 + 400
        )
        self.assertEqual(parse_clock("00:00:00"), 0)

    def test_rejects_a_bad_clock(self):
        with self.assertRaises(LogError):
            parse_clock("9:15")
        with self.assertRaises(LogError):
            parse_clock("24:00:00")


class LineTests(unittest.TestCase):
    def test_phase_can_sit_before_attributes(self):
        event = parse_line("12:01:02.100 web request start path=/", 1)
        self.assertEqual(event.name, "web request")
        self.assertEqual(event.phase, "start")
        self.assertEqual(event.attributes, {"path": "/"})

    def test_phase_can_sit_at_the_end(self):
        event = parse_line("12:01:02.100 web request path=/ start", 1)
        self.assertEqual(event.phase, "start")
        self.assertEqual(event.attributes["path"], "/")

    def test_numbers_stay_numbers(self):
        event = parse_line("12:00:00.000 db query event rows=3 wait=1.5", 4)
        self.assertEqual(event.attributes["rows"], 3)
        self.assertEqual(event.attributes["wait"], 1.5)

    def test_non_numbers_stay_text(self):
        event = parse_line(
            "12:00:00.000 sample event loss=nan note=infinity mark=²", 5
        )
        self.assertEqual(event.attributes["loss"], "nan")
        self.assertEqual(event.attributes["note"], "infinity")
        self.assertEqual(event.attributes["mark"], "²")

    def test_a_name_without_a_phase_is_an_event(self):
        event = parse_line("12:00:00.000 cache hit key=user", 1)
        self.assertEqual(event.phase, "event")
        self.assertEqual(event.name, "cache hit")

    def test_comments_and_blanks_are_skipped(self):
        events = parse_log("# note\n\n12:00:00.000 ping start\n")
        self.assertEqual(len(events), 1)

    def test_events_are_sorted_by_clock_but_keep_line_order(self):
        events = parse_log("00:00:02.000 b event\n00:00:01.000 a event\n")
        self.assertEqual([event.name for event in events], ["a", "b"])

    def test_a_single_name_is_a_point_event(self):
        event = parse_line("12:00:00.000 only", 3)
        self.assertEqual((event.name, event.phase), ("only", "event"))

    def test_attribute_without_a_value_marker_is_an_error(self):
        with self.assertRaises(LogError):
            parse_line("12:00:00.000 ping start nope", 2)


if __name__ == "__main__":
    unittest.main()
