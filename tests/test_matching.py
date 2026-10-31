"""Tests for predictor.matching.  Run with:  python -m unittest"""

import json
import unittest
from pathlib import Path

from predictor.matching import ConstituencyMatcher, name_key

DATA = Path(__file__).resolve().parent.parent / "data"


def known_seats():
    with open(DATA / "UKDecember2019.json", encoding="utf-8") as f:
        return [s["constituency"] for s in json.load(f)["constituencies"]]


class NameKeyTests(unittest.TestCase):
    def test_drops_and_ampersand_the_and_sorts(self):
        self.assertEqual(name_key("Hull North & Cottingham"), "cottingham hull north")
        self.assertEqual(
            name_key("Bridlington and The Wolds"), name_key("Bridlington and the Wolds")
        )

    def test_repairs_garbled_text_and_accents(self):
        self.assertEqual(name_key("Ynys MÃ´n"), "mon ynys")
        self.assertEqual(name_key("Ynys Môn"), "mon ynys")
        self.assertEqual(name_key("Ynys Mon"), "mon ynys")


class OwnDataTests(unittest.TestCase):
    """Faults in our own seat list must stop the program."""

    def test_clashing_names_stop_the_program(self):
        with self.assertRaises(ValueError) as caught:
            ConstituencyMatcher(["Hull North & Cottingham", "Cottingham and Hull North"])
        self.assertIn("Cottingham and Hull North", str(caught.exception))

    def test_our_2019_names_do_not_clash(self):
        ConstituencyMatcher(known_seats())  # would raise if two names clashed


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matcher = ConstituencyMatcher(known_seats())

    def test_fallback_on_missing_words(self):
        self.assertEqual(self.matcher.match("Hull East"), "Kingston upon Hull East")
        self.assertEqual(
            self.matcher.match("Hull West & Haltemprice"),
            "Kingston upon Hull West and Haltemprice",
        )

    def test_unknown_name_returns_none_and_is_recorded(self):
        with self.assertLogs("predictor.matching", "WARNING"):
            self.assertIsNone(self.matcher.match("Atlantis Central"))
        self.assertIn("Atlantis Central", self.matcher.unmatched)

    def test_ambiguous_name_returns_none(self):
        with self.assertLogs("predictor.matching", "WARNING"):
            self.assertIsNone(self.matcher.match("Leicester"))
        self.assertIn("could be any of", self.matcher.unmatched["Leicester"])

    def test_bad_input_never_raises(self):
        with self.assertLogs("predictor.matching", "WARNING"):
            for bad in (None, 123, "", "   ", "&", ["a list"], {"a": 1}):
                self.assertIsNone(self.matcher.match(bad))

    def test_every_2024_seat_matches_a_different_seat(self):
        with open(DATA / "raw" / "UKJuly2024.json", encoding="utf-8") as f:
            live_names = list(json.load(f))
        matched = [self.matcher.match(name) for name in live_names]
        self.assertEqual(len(set(matched)), 650)


if __name__ == "__main__":
    unittest.main()
