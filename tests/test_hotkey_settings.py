import unittest

from hotkey_settings import format_hotkey


class HotkeySettingsTests(unittest.TestCase):
    def test_formats_modifier_combo(self):
        self.assertEqual(format_hotkey("1", 0x4 | 0x8), "ctrl+alt+1")

    def test_formats_shifted_function_key(self):
        self.assertEqual(format_hotkey("F5", 0x1), "shift+f5")

    def test_ignores_modifier_only_keypress(self):
        self.assertIsNone(format_hotkey("Control_L", 0x4))

    def test_uses_keyboard_library_key_names(self):
        self.assertEqual(format_hotkey("Escape", 0), "esc")
        self.assertEqual(format_hotkey("Return", 0), "enter")


if __name__ == "__main__":
    unittest.main()
