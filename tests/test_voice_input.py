import unittest
from unittest.mock import patch

from protocols import PROTOCOLS
from voice_input import VoiceInput, _CANCEL_COMMAND, _voice_commands


class VoiceInputTests(unittest.TestCase):
    def test_commands_cover_protocol_names_numbers_and_cancel(self):
        commands = _voice_commands()
        self.assertEqual(commands["cancel"], _CANCEL_COMMAND)
        self.assertEqual(commands["kilo delta one zero one"], "KD-101")
        self.assertEqual(commands["kilo delta eins null eins"], "KD-101")
        self.assertEqual(commands["eins"], "KD-101")
        self.assertEqual(commands["lockdown"], "KD-101")
        self.assertEqual(len({commands[protocol.number] for protocol in PROTOCOLS}), 11)

    def test_voice_input_reports_non_windows_platform(self):
        voice_input = VoiceInput(lambda _: None, lambda _: None)
        with patch("voice_input.os.name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                voice_input.start()


if __name__ == "__main__":
    unittest.main()
