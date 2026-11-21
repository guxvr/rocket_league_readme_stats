import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import scraper


def profile(name=None):
    return {"data": {"platformInfo": {"platformUserHandle": name or scraper.DISPLAY_NAME},
                     "segments": [{"attributes": {"playlistId": 11},
                                   "stats": {"rating": {"value": 1234},
                                             "tier": {"metadata": {"name": "Champion II"}}}}]}}


class ScraperTests(unittest.TestCase):
    def test_paid_layer_disabled_even_with_key(self):
        with patch.dict(os.environ, {"SCRAPER_API_KEY": "secret", "ENABLE_SCRAPER_API": "false"}), patch("requests.get") as get:
            self.assertEqual(scraper._scrape_layer3(), {})
            get.assert_not_called()

    def test_import_validates_identity_and_does_not_use_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            with patch.dict(os.environ, {"TRN_STATS_FILE": str(path)}), patch.object(scraper, "_scrape_layer1") as network:
                path.write_text(json.dumps(profile()), encoding="utf-8")
                result = scraper.fetch_stats()
                self.assertTrue(result["success"])
                self.assertEqual(result["modes"]["2v2"]["mmr"], 1234)
                self.assertIsNone(result["modes"]["1v1"])
                path.write_text(json.dumps(profile("someone else")), encoding="utf-8")
                self.assertFalse(scraper.fetch_stats()["success"])
                path.write_text("not json", encoding="utf-8")
                self.assertFalse(scraper.fetch_stats()["success"])
                network.assert_not_called()

    def test_grand_champion_sprite_exists(self):
        sprite = scraper._rank_to_sprite("Grand Champion II")
        self.assertTrue((Path(__file__).resolve().parents[1] / "sprites" / sprite).exists())


if __name__ == "__main__":
    unittest.main()
