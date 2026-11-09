import unittest

from otl.page import render_page


class PageTests(unittest.TestCase):
    def test_escapes_and_keeps_a_fenced_block(self):
        page = render_page(
            "A <trace>",
            "Heading\n\n```\n1 < 2\n```\n",
            "lead & more",
        )
        self.assertIn("<title>A &lt;trace&gt;</title>", page)
        self.assertIn('<p class="lead">lead &amp; more</p>', page)
        self.assertIn("<h2>Heading</h2>", page)
        self.assertIn("<pre>1 &lt; 2</pre>", page)
        self.assertNotIn("<script", page)

    def test_a_rule_starts_a_new_section(self):
        page = render_page("T", "First\n\n---\nSecond\n\nbody\n")
        self.assertEqual(page.count("<section>"), 2)
        self.assertIn("<h2>Second</h2>", page)
        self.assertIn("<p>body</p>", page)


if __name__ == "__main__":
    unittest.main()
