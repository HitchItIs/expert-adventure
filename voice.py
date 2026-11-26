import queue
import threading


class Voice:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._queue = queue.Queue()
        self._thread = None

    def start(self):
        if self.enabled and (self._thread is None or not self._thread.is_alive()):
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def say(self, text):
        if self.enabled:
            self.start()
            self._queue.put(text)

    def _worker(self):
        try:
            import pyttsx3

            engine = pyttsx3.init()
        except Exception:
            self.enabled = False
            return

        while True:
            text = self._queue.get()
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                self.enabled = False
                return
            finally:
                self._queue.task_done()
