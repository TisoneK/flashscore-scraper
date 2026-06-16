"""Tests for the JSON storage module."""
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.models import MatchModel, OddsModel, H2HMatchModel
from src.storage.json_storage import JSONStorage


class TestJSONStorageInit(unittest.TestCase):
    """Test JSONStorage initialization."""

    def test_init_creates_base_dir(self):
        """Test that initialization creates the base directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = os.path.join(tmpdir, "json_output")
            self.assertFalse(os.path.exists(base))
            storage = JSONStorage(base_dir=base)
            self.assertTrue(os.path.exists(base))

    def test_init_existing_dir(self):
        """Test that initialization works with an existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(base_dir=tmpdir)
            self.assertTrue(os.path.exists(tmpdir))

    def test_default_base_dir(self):
        """Test the default base directory value."""
        storage = JSONStorage(base_dir="output/json")
        self.assertEqual(storage.base_dir, Path("output/json"))


class TestSaveMatches(unittest.TestCase):
    """Test saving matches to JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = JSONStorage(base_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_match(self, match_id="m1", status="complete", skip_reason=None):
        """Helper to create a test match."""
        return MatchModel.create(
            match_id=match_id,
            country="USA",
            league="NBA",
            home_team="Lakers",
            away_team="Celtics",
            date="2026-06-06",
            time="20:00",
            status=status,
            skip_reason=skip_reason,
        )

    def test_save_complete_match_creates_file(self):
        """Test that saving a complete match creates a JSON file."""
        match = self._make_match()
        result = self.storage.save_matches([match], filename="test_save.json")
        self.assertTrue(result)
        filepath = Path(self.tmpdir) / "test_save.json"
        self.assertTrue(filepath.exists())

    def test_save_complete_match_data_structure(self):
        """Test the data structure of a saved complete match."""
        match = self._make_match()
        self.storage.save_matches([match], filename="test_structure.json")
        filepath = Path(self.tmpdir) / "test_structure.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("matches", data)
        self.assertIn("metadata", data)
        self.assertEqual(len(data["matches"]), 1)
        self.assertEqual(data["matches"][0]["match_id"], "m1")
        self.assertEqual(data["matches"][0]["country"], "USA")
        self.assertEqual(data["matches"][0]["league"], "NBA")

    def test_save_incomplete_match_goes_to_skipped(self):
        """Test that an incomplete match goes to skipped_matches, not matches."""
        match = self._make_match(match_id="m2", status="incomplete", skip_reason="no odds")
        self.storage.save_matches([match], filename="test_incomplete.json")
        filepath = Path(self.tmpdir) / "test_incomplete.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["matches"]), 0)
        skipped = data["metadata"]["skipped_matches"]["details"]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["match_id"], "m2")
        self.assertEqual(skipped[0]["reason"], "no odds")

    def test_save_complete_and_incomplete_together(self):
        """Test saving a mix of complete and incomplete matches."""
        complete = self._make_match(match_id="c1", status="complete")
        incomplete = self._make_match(match_id="i1", status="incomplete", skip_reason="no H2H")
        self.storage.save_matches([complete, incomplete], filename="test_mixed.json")
        filepath = Path(self.tmpdir) / "test_mixed.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["matches"]), 1)
        self.assertEqual(data["matches"][0]["match_id"], "c1")
        skipped = data["metadata"]["skipped_matches"]["details"]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["match_id"], "i1")

    def test_save_updates_existing_file(self):
        """Test that saving to an existing file merges data correctly."""
        match1 = self._make_match(match_id="m1")
        self.storage.save_matches([match1], filename="test_update.json")

        match2 = self._make_match(match_id="m2")
        self.storage.save_matches([match2], filename="test_update.json")

        filepath = Path(self.tmpdir) / "test_update.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["matches"]), 2)
        match_ids = {m["match_id"] for m in data["matches"]}
        self.assertEqual(match_ids, {"m1", "m2"})

    def test_save_overwrites_complete_match(self):
        """Test that re-saving a match with the same ID overwrites it."""
        match_v1 = self._make_match(match_id="m1")
        match_v1.home_team = "Lakers"
        self.storage.save_matches([match_v1], filename="test_overwrite.json")

        match_v2 = self._make_match(match_id="m1")
        match_v2.home_team = "Warriors"
        self.storage.save_matches([match_v2], filename="test_overwrite.json")

        filepath = Path(self.tmpdir) / "test_overwrite.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["matches"]), 1)
        self.assertEqual(data["matches"][0]["home_team"], "Warriors")

    def test_complete_match_removes_from_skipped(self):
        """Test that completing a previously skipped match removes it from skipped list."""
        incomplete = self._make_match(match_id="m1", status="incomplete", skip_reason="no odds")
        self.storage.save_matches([incomplete], filename="test_promote.json")

        complete = self._make_match(match_id="m1", status="complete")
        self.storage.save_matches([complete], filename="test_promote.json")

        filepath = Path(self.tmpdir) / "test_promote.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["matches"]), 1)
        self.assertEqual(data["matches"][0]["match_id"], "m1")
        skipped = data["metadata"]["skipped_matches"]["details"]
        self.assertEqual(len(skipped), 0)

    def test_save_empty_match_list(self):
        """Test saving an empty match list."""
        result = self.storage.save_matches([], filename="test_empty.json")
        self.assertTrue(result)
        filepath = Path(self.tmpdir) / "test_empty.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["matches"]), 0)

    def test_metadata_fields_populated(self):
        """Test that metadata fields are correctly populated."""
        match = self._make_match()
        self.storage.save_matches([match], filename="test_meta.json")
        filepath = Path(self.tmpdir) / "test_meta.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data["metadata"]
        self.assertEqual(meta["total_matches"], 1)
        self.assertIn("last_update", meta)
        self.assertIn("file_info", meta)
        self.assertEqual(meta["file_info"]["filename"], "test_meta.json")
        self.assertIn("size_bytes", meta["file_info"])

    def test_save_match_with_odds(self):
        """Test saving a match with odds data."""
        odds = OddsModel(match_id="m1", home_odds=1.85, away_odds=2.10, over_odds=1.90, under_odds=1.90, match_total=210.5)
        match = self._make_match(match_id="m1")
        match.odds = odds
        self.storage.save_matches([match], filename="test_odds.json")
        filepath = Path(self.tmpdir) / "test_odds.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved_match = data["matches"][0]
        self.assertIn("odds", saved_match)
        self.assertEqual(saved_match["odds"]["home_odds"], 1.85)
        self.assertEqual(saved_match["odds"]["match_total"], 210.5)

    def test_save_match_with_h2h(self):
        """Test saving a match with H2H data."""
        h2h = H2HMatchModel(match_id="m1", date="2025-12-01", home_team="Lakers", away_team="Celtics", home_score=110, away_score=105, competition="NBA")
        match = self._make_match(match_id="m1")
        match.h2h_matches = [h2h]
        self.storage.save_matches([match], filename="test_h2h.json")
        filepath = Path(self.tmpdir) / "test_h2h.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved_match = data["matches"][0]
        self.assertIn("h2h_matches", saved_match)
        self.assertEqual(len(saved_match["h2h_matches"]), 1)
        self.assertEqual(saved_match["h2h_matches"][0]["home_score"], 110)


class TestGetProcessedMatchIds(unittest.TestCase):
    """Test getting processed match IDs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = JSONStorage(base_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_match(self, match_id="m1", status="complete", skip_reason=None):
        return MatchModel.create(
            match_id=match_id,
            country="USA",
            league="NBA",
            home_team="Lakers",
            away_team="Celtics",
            date="2026-06-06",
            time="20:00",
            status=status,
            skip_reason=skip_reason,
        )

    def test_empty_file_returns_empty_set(self):
        """Test that an empty file returns an empty set."""
        result = self.storage.get_processed_match_ids(filename="nonexistent.json")
        self.assertEqual(result, set())

    def test_returns_complete_match_ids(self):
        """Test that complete match IDs are returned."""
        match = self._make_match(match_id="m1")
        self.storage.save_matches([match], filename="test_ids.json")
        result = self.storage.get_processed_match_ids(filename="test_ids.json")
        match_ids = {mid for mid, _ in result}
        self.assertIn("m1", match_ids)

    def test_returns_skipped_match_ids(self):
        """Test that skipped match IDs are returned with reasons."""
        match = self._make_match(match_id="s1", status="incomplete", skip_reason="no odds")
        self.storage.save_matches([match], filename="test_skipped_ids.json")
        result = self.storage.get_processed_match_ids(filename="test_skipped_ids.json")
        result_dict = dict(result)
        self.assertIn("s1", result_dict)
        self.assertEqual(result_dict["s1"], "no odds")

    def test_returns_both_complete_and_skipped(self):
        """Test that both complete and skipped match IDs are returned."""
        complete = self._make_match(match_id="c1")
        skipped = self._make_match(match_id="s1", status="incomplete", skip_reason="no H2H")
        self.storage.save_matches([complete, skipped], filename="test_all_ids.json")
        result = self.storage.get_processed_match_ids(filename="test_all_ids.json")
        match_ids = {mid for mid, _ in result}
        self.assertEqual(match_ids, {"c1", "s1"})


class TestLoadMatches(unittest.TestCase):
    """Test loading matches from JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = JSONStorage(base_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_saved_matches(self):
        """Test loading matches that were previously saved."""
        match = MatchModel.create(
            match_id="m1",
            country="USA",
            league="NBA",
            home_team="Lakers",
            away_team="Celtics",
            date="2026-06-06",
            time="20:00",
        )
        self.storage.save_matches([match], filename="test_load.json")
        loaded = self.storage.load_matches("test_load.json")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].match_id, "m1")
        self.assertEqual(loaded[0].home_team, "Lakers")

    def test_load_nonexistent_file_raises(self):
        """Test that loading a nonexistent file raises an error."""
        with self.assertRaises(Exception):
            self.storage.load_matches("nonexistent.json")


class TestSaveResults(unittest.TestCase):
    """Test saving results data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = JSONStorage(base_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_results_creates_file(self):
        """Test that save_results creates a valid JSON file."""
        results = [
            {"match_id": "m1", "home_score": 110, "away_score": 105},
            {"match_id": "m2", "home_score": 98, "away_score": 102},
        ]
        result = self.storage.save_results(results, "results.json")
        self.assertTrue(result)
        filepath = Path(self.tmpdir) / "results.json"
        self.assertTrue(filepath.exists())

    def test_save_results_data_structure(self):
        """Test the data structure of saved results."""
        results = [{"match_id": "m1", "home_score": 110, "away_score": 105}]
        self.storage.save_results(results, "results_structure.json")
        filepath = Path(self.tmpdir) / "results_structure.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("results", data)
        self.assertIn("metadata", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["match_id"], "m1")
        self.assertEqual(data["metadata"]["total_results"], 1)

    def test_save_results_empty_list(self):
        """Test saving an empty results list."""
        result = self.storage.save_results([], "empty_results.json")
        self.assertTrue(result)
        filepath = Path(self.tmpdir) / "empty_results.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["results"]), 0)
        self.assertEqual(data["metadata"]["total_results"], 0)


class TestDailyFilepath(unittest.TestCase):
    """Test the daily filepath generation."""

    def test_daily_filepath_format(self):
        """Test that the daily filepath uses today's date (YYYYMMDD format)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(base_dir=tmpdir)
            filepath = storage._get_daily_filepath()
            today = datetime.now().strftime("%Y%m%d")
            expected = Path(tmpdir) / f"matches_{today}.json"
            self.assertEqual(filepath, expected)

    def test_daily_filepath_tomorrow(self):
        """Test that the daily filepath uses tomorrow's date when day='Tomorrow'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(base_dir=tmpdir)
            filepath = storage._get_daily_filepath(day="Tomorrow")
            tomorrow = (datetime.now() + __import__('datetime').timedelta(days=1)).strftime("%Y%m%d")
            expected = Path(tmpdir) / f"matches_{tomorrow}.json"
            self.assertEqual(filepath, expected)


if __name__ == "__main__":
    unittest.main()
