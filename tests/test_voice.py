import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from voice import Voice


class VoiceTests(unittest.TestCase):
    def test_speaks_queued_text_and_closes_cleanly(self):
        messages = []
        engine = MagicMock()
        pyttsx3 = SimpleNamespace(init=MagicMock(return_value=engine))
        voice = Voice(log=messages.append)

        with patch.dict(sys.modules, {"pyttsx3": pyttsx3}):
            self.assertTrue(voice.say("test phrase"))
            voice.close()

        engine.say.assert_called_once_with("test phrase")
        engine.runAndWait.assert_called_once_with()
        engine.stop.assert_called_once_with()
        self.assertIn("Voice output ready.", messages)

    def test_reports_speech_engine_initialization_failure(self):
        messages = []
        pyttsx3 = SimpleNamespace(
            init=MagicMock(side_effect=RuntimeError("speech engine missing"))
        )
        voice = Voice(log=messages.append)

        with patch.dict(sys.modules, {"pyttsx3": pyttsx3}):
            self.assertTrue(voice.say("test phrase"))
            voice.close()

        self.assertFalse(voice.enabled)
        self.assertTrue(any("speech engine missing" in message for message in messages))

    def test_disabled_voice_does_not_queue_speech(self):
        voice = Voice(enabled=False)

        self.assertFalse(voice.say("test phrase"))
        self.assertIsNone(voice._thread)


if __name__ == "__main__":
    unittest.main()
