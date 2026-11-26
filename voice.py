import os
import queue
import threading


_STOP = object()


class Voice:
    def __init__(self, enabled=True, log=None):
        self.enabled = bool(enabled)
        self._log = log or (lambda _: None)
        self._queue = queue.Queue()
        self._thread = None
        self._lock = threading.Lock()
        self._closing = False

    def _start_locked(self):
        if self.enabled and not self._closing and (
            self._thread is None or not self._thread.is_alive()
        ):
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def start(self):
        with self._lock:
            self._start_locked()

    def set_enabled(self, enabled):
        with self._lock:
            self.enabled = bool(enabled)

    def say(self, text):
        with self._lock:
            if not self.enabled or self._closing:
                return False
            self._start_locked()
            self._queue.put(str(text))
        return True

    def close(self):
        with self._lock:
            if self._closing:
                return
            self._closing = True
            thread = self._thread
            if thread and thread.is_alive():
                self._queue.put(_STOP)
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5)

    def _disable(self):
        with self._lock:
            self.enabled = False

    def _discard_pending(self):
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return
            else:
                self._queue.task_done()

    def _worker(self):
        try:
            import pyttsx3

            engine = (
                pyttsx3.init("sapi5")
                if os.name == "nt"
                else pyttsx3.init()
            )
        except Exception as exc:
            self._disable()
            self._log(f"Voice output unavailable: {exc}")
            self._discard_pending()
            return

        self._log("Voice output ready.")
        while True:
            text = self._queue.get()
            if text is _STOP:
                self._queue.task_done()
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                self._disable()
                self._log(f"Voice output failed: {exc}")
                self._queue.task_done()
                self._discard_pending()
                return
            self._queue.task_done()

        try:
            engine.stop()
        except Exception as exc:
            self._log(f"Voice cleanup failed: {exc}")
