import unittest
from unittest.mock import MagicMock

from main import TacticalOpsApp
from protocols import PROTOCOLS


class CommandTests(unittest.TestCase):
    def make_app(self, command):
        app = object.__new__(TacticalOpsApp)
        app.command_value = MagicMock()
        app.command_value.get.return_value = command
        app.logs = MagicMock()
        app.runner = MagicMock()
        return app

    def test_help_explains_console_commands(self):
        app = self.make_app("help")

        app.submit_command()

        message = app.logs.put.call_args.args[0]
        for command in ("list", "status", "run", "mode", "voice", "settings", "cancel", "quit"):
            with self.subTest(command=command):
                self.assertIn(command, message)

    def test_list_explains_each_protocol(self):
        app = self.make_app("list")

        app.submit_command()

        messages = [call.args[0] for call in app.logs.put.call_args_list]
        self.assertEqual(len(messages), len(PROTOCOLS))
        for protocol, message in zip(PROTOCOLS, messages):
            with self.subTest(protocol=protocol.code):
                self.assertIn(protocol.code, message)
                self.assertIn(protocol.description, message)

    def test_run_prefix_accepts_protocol_code(self):
        app = self.make_app("run AO-07")

        app.submit_command()

        app.runner.start.assert_called_once_with("AO-07")


if __name__ == "__main__":
    unittest.main()
