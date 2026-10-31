"""Tests for predictor.matching.  Run with:  python -m unittest"""

import json
import unittest
from pathlib import Path

from predictor.matching import ConstituencyMatcher, NoMatchError, name_key

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

    def test_unknown_name_raises(self):
        with self.assertRaises(NoMatchError):
            self.matcher.match("Atlantis Central")

    def test_ambiguous_name_raises(self):
        with self.assertRaises(NoMatchError):
            self.matcher.match("Leicester")

    def test_every_2024_seat_matches_a_different_seat(self):
        with open(DATA / "raw" / "UKJuly2024.json", encoding="utf-8") as f:
            live_names = list(json.load(f))
        matched = [self.matcher.match(name) for name in live_names]
        self.assertEqual(len(set(matched)), 650)


if __name__ == "__main__":
    unittest.main()
