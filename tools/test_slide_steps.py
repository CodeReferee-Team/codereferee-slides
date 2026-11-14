import re
import unittest
from pathlib import Path


HTML = (Path(__file__).parents[1] / "index.html").read_text()


class SlideStepTests(unittest.TestCase):
    def test_slide_2_load_animation_starts_at_step_1(self):
        hook = re.search(r"s2\(st\)\{(?P<body>.*?)\n\s*s7\(st\)", HTML, re.DOTALL)

        self.assertIsNotNone(hook)
        self.assertIn("if(st<1)", hook.group("body"))
        self.assertNotRegex(HTML, r"\bs2\(\)\{")


if __name__ == "__main__":
    unittest.main()
