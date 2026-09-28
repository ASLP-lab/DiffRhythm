import importlib.util
import unittest
from pathlib import Path


def _load_num():
    path = Path(__file__).resolve().parent / "thirdparty" / "LangSegment" / "utils" / "num.py"
    spec = importlib.util.spec_from_file_location("diffrhythm_num", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


num = _load_num()


class TestCurrency(unittest.TestCase):
    def test_a_decimal_keeps_the_zero_after_the_point(self):
        self.assertEqual(num.verbalize_amount("1.05"), "一点零五")
        self.assertEqual(num.verbalize_amount("10.01"), "十点零一")
        self.assertEqual(num.verbalize_amount("0.05"), "零点零五")

    def test_a_trailing_zero_after_the_point_is_dropped(self):
        self.assertEqual(num.verbalize_amount("12.50"), "十二点五")
        self.assertEqual(num.verbalize_amount("1.5"), "一点五")

    def test_an_integer_amount_is_unchanged(self):
        self.assertEqual(num.verbalize_amount("100"), "一百")
        self.assertEqual(num.verbalize_amount("10"), "十")


if __name__ == "__main__":
    unittest.main()
