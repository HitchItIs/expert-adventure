import json
import tempfile
import unittest
from pathlib import Path

from main import default_config, load_config


class ConfigTests(unittest.TestCase):
    def test_first_run_config_is_safe_and_has_default_hotkeys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = load_config(path)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(config["test_mode"])
        self.assertFalse(config["allow_destructive_actions"])
        self.assertEqual(config["hotkeys"]["KD-101"], "ctrl+alt+1")
        self.assertEqual(saved, config)

    def test_default_config_is_independent_between_calls(self):
        first = default_config()
        second = default_config()
        first["hotkeys"]["KD-101"] = "ctrl+shift+x"
        self.assertEqual(second["hotkeys"]["KD-101"], "ctrl+alt+1")


if __name__ == "__main__":
    unittest.main()
