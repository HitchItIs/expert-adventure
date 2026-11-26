class Hotkeys:
    def __init__(self, config, activate, toggle_test_mode):
        self.config = config
        self.activate = activate
        self.toggle_test_mode = toggle_test_mode
        self._keyboard = None
        self._registered = []

    def start(self):
        try:
            import keyboard
        except ImportError as exc:
            raise RuntimeError("Install the keyboard package to use global hotkeys.") from exc

        self._keyboard = keyboard
        try:
            for code, key in self.config.get("hotkeys", {}).items():
                if not key:
                    continue
                callback = self.toggle_test_mode if code == "TEST" else lambda item=code: self.activate(item)
                keyboard.add_hotkey(key, callback, suppress=False)
                self._registered.append(key)
        except (ImportError, ValueError, OSError) as exc:
            self.stop()
            raise RuntimeError(f"Could not register hotkey {key!r}: {exc}") from exc

    def stop(self):
        if self._keyboard is None:
            return
        for key in self._registered:
            self._keyboard.remove_hotkey(key)
        self._registered.clear()
