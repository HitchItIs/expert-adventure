import unittest
from unittest.mock import MagicMock, patch

from protocols import PROTOCOLS
from voice_input import VoiceInput, _CANCEL_COMMAND, _voice_commands


class VoiceInputTests(unittest.TestCase):
    def test_commands_require_full_protocol_phrases_and_cancel(self):
        commands = _voice_commands()
        self.assertEqual(commands["cancel"], _CANCEL_COMMAND)
        self.assertEqual(commands["kilo delta one zero one"], "KD-101")
        self.assertEqual(commands["kilo delta eins null eins"], "KD-101")
        self.assertEqual(commands["kd 101"], "KD-101")
        self.assertNotIn("eins", commands)
        self.assertNotIn("lockdown", commands)
        for protocol in PROTOCOLS:
            with self.subTest(protocol=protocol.code):
                self.assertEqual(
                    commands[protocol.name.replace("-", " ").casefold()],
                    protocol.code,
                )

    def test_listener_restarts_after_unexpected_process_exit(self):
        class FakeProcess:
            def __init__(self, output, returncode):
                self.stdout = iter(output)
                self.returncode = returncode

            def poll(self):
                return self.returncode

            def terminate(self):
                self.returncode = -15

            def wait(self):
                return self.returncode

        messages = []
        commands = []
        def capture_command(command):
            commands.append(command)
            voice_input._stopping.set()

        voice_input = VoiceInput(capture_command, messages.append)
        voice_input._stopping.wait = MagicMock(return_value=False)
        processes = [
            FakeProcess([], 1),
            FakeProcess(["__VOICE_READY__", "KD-101"], 0),
        ]
        with patch("voice_input.subprocess.Popen", side_effect=processes) as popen:
            voice_input._listen()

        self.assertEqual(popen.call_count, 2)
        self.assertEqual(commands, ["KD-101"])
        self.assertTrue(any("restarting" in message for message in messages))

    def test_voice_input_reports_non_windows_platform(self):
        voice_input = VoiceInput(lambda _: None, lambda _: None)
        with patch("voice_input.os.name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                voice_input.start()


if __name__ == "__main__":
    unittest.main()
