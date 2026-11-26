import unittest
from unittest.mock import MagicMock, patch

import protocols
from protocols import PROTOCOLS, ProtocolRunner, resolve_protocol


class VoiceSpy:
    def __init__(self):
        self.messages = []

    def say(self, text):
        self.messages.append(text)


class ProtocolTests(unittest.TestCase):
    def test_all_protocols_resolve_by_code_alias_and_number(self):
        self.assertEqual(len(PROTOCOLS), 11)
        for protocol in PROTOCOLS:
            with self.subTest(protocol=protocol.code):
                self.assertIs(resolve_protocol(protocol.code), protocol)
                self.assertIs(resolve_protocol(protocol.alias), protocol)
                self.assertIs(resolve_protocol(protocol.number), protocol)

    def test_unknown_protocol_is_rejected(self):
        self.assertIsNone(resolve_protocol("not-a-protocol"))

    def test_test_mode_simulates_lockdown_without_calling_windows(self):
        messages = []
        voice = VoiceSpy()
        runner = ProtocolRunner({"test_mode": True}, messages.append, voice)
        runner.execute(resolve_protocol("KD-101"))
        self.assertTrue(any("simulated" in message for message in messages))
        self.assertIn("Kilo-Delta-101 bestätigt. System verriegelt.", voice.messages)
        self.assertTrue(any("sequence complete" in message for message in messages))

    def test_live_mode_still_blocks_destructive_actions_without_opt_in(self):
        messages = []
        runner = ProtocolRunner(
            {"test_mode": False, "allow_destructive_actions": False},
            messages.append,
            VoiceSpy(),
        )
        runner.execute(resolve_protocol("KD-101"))
        self.assertEqual(sum("Blocked" in message for message in messages), 1)

    def test_live_lockdown_locks_workstation_without_clearing_clipboard_opt_in(self):
        messages = []
        runner = ProtocolRunner(
            {"test_mode": False, "allow_destructive_actions": False},
            messages.append,
            VoiceSpy(),
        )
        runner._clear_clipboard = MagicMock()
        runner._lock_workstation = MagicMock()
        with patch.object(protocols.os, "name", "nt"):
            runner.lockdown()
        runner._clear_clipboard.assert_not_called()
        runner._lock_workstation.assert_called_once_with()
        self.assertTrue(any("Clipboard cleared" in message and "Blocked" in message for message in messages))

    def test_simulated_protocol_is_not_reported_as_cancelled(self):
        messages = []
        runner = ProtocolRunner({"test_mode": True}, messages.append, VoiceSpy())
        runner.execute(resolve_protocol("KD-101"))
        self.assertFalse(any("sequence cancelled" in message for message in messages))
        self.assertTrue(any("sequence complete" in message for message in messages))

    def test_restarting_night_mode_cancels_the_previous_shutdown_timer(self):
        runner = ProtocolRunner(
            {
                "test_mode": False,
                "allow_destructive_actions": True,
                "shutdown_timer_seconds": 5,
            },
            lambda _: None,
            VoiceSpy(),
        )
        runner._perform = MagicMock(return_value=False)
        first_timer = MagicMock()
        second_timer = MagicMock()
        with patch.object(protocols.os, "name", "nt"), patch.object(
            protocols.threading, "Timer", side_effect=[first_timer, second_timer]
        ):
            runner.night_mode()
            runner.night_mode()
        first_timer.cancel.assert_called_once_with()
        second_timer.start.assert_called_once_with()
        self.assertIs(runner._shutdown_timer, second_timer)
        runner.cancel()
        second_timer.cancel.assert_called_once_with()
        self.assertIsNone(runner._shutdown_timer)


if __name__ == "__main__":
    unittest.main()
