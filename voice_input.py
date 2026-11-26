import base64
import json
import os
import subprocess
import threading
from itertools import product

from protocols import PROTOCOLS


_POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Speech
    $json = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__COMMAND_DATA__'))
    $parsed = $json | ConvertFrom-Json
    $commandMap = @{}
    foreach ($property in $parsed.PSObject.Properties) {
        $commandMap[$property.Name] = [string]$property.Value
    }
    $choices = New-Object System.Speech.Recognition.Choices
    foreach ($phrase in $commandMap.Keys) {
        [void]$choices.Add($phrase)
    }
    $builder = New-Object System.Speech.Recognition.GrammarBuilder
    [void]$builder.Append($choices)
    $grammar = New-Object System.Speech.Recognition.Grammar($builder)
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    $recognizer.LoadGrammar($grammar)
    $recognizer.SetInputToDefaultAudioDevice()
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new()
    Write-Output '__VOICE_READY__'
    while ($true) {
        $result = $recognizer.Recognize()
        if ($result -and $commandMap.ContainsKey($result.Text)) {
            Write-Output $commandMap[$result.Text]
        }
    }
} catch {
    Write-Output ('__VOICE_ERROR__' + $_.Exception.Message)
    exit 1
}
"""

_CANCEL_COMMAND = "__CANCEL__"


def _voice_commands():
    commands = {"cancel": _CANCEL_COMMAND}
    number_words = {
        "0": (("zero", "oh"), ("null",)),
        "1": (("one",), ("eins",)),
        "2": (("two",), ("zwei",)),
        "3": (("three",), ("drei",)),
        "4": (("four",), ("vier",)),
        "5": (("five",), ("fünf", "fuenf")),
        "6": (("six",), ("sechs",)),
        "7": (("seven",), ("sieben",)),
        "8": (("eight",), ("acht",)),
        "9": (("nine",), ("neun",)),
    }
    for protocol in PROTOCOLS:
        phrases = {
            protocol.name.replace("-", " "),
            protocol.alias.replace("-", " "),
            protocol.code.replace("-", " "),
            protocol.description,
            protocol.number,
        }
        name_prefix = " ".join(protocol.name.split("-")[:-1])
        digits = protocol.name.split("-")[-1]
        if digits.isdigit() and len(digits) > 1:
            for language_index in (0, 1):
                options = [number_words[digit][language_index] for digit in digits]
                for spoken_digits in product(*options):
                    phrases.add(f"{name_prefix} {' '.join(spoken_digits)}")
        if protocol.number in number_words:
            phrases.update(
                word
                for language in number_words[protocol.number]
                for word in language
            )
        for phrase in phrases:
            commands[phrase.casefold()] = protocol.code
    return commands


class VoiceInput:
    def __init__(self, on_command, log):
        self.on_command = on_command
        self.log = log
        self._process = None
        self._thread = None
        self._lock = threading.Lock()
        self._stopping = threading.Event()

    def start(self):
        if os.name != "nt":
            raise RuntimeError("Voice input requires Windows speech recognition.")
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stopping.clear()
            self._thread = threading.Thread(target=self._listen, daemon=True)
            self._thread.start()

    def stop(self):
        self._stopping.set()
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError as exc:
                self.log(f"Voice input stop failed: {exc}")
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)

    def _listen(self):
        command_json = json.dumps(_voice_commands(), ensure_ascii=True)
        command_data = base64.b64encode(command_json.encode("utf-8")).decode("ascii")
        script = _POWERSHELL_SCRIPT.replace("__COMMAND_DATA__", command_data)
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        args = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded_script,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
        except OSError as exc:
            self.log(f"Voice input unavailable: {exc}")
            return

        with self._lock:
            self._process = process
        try:
            if self._stopping.is_set():
                process.terminate()
            for output in process.stdout:
                message = output.strip()
                if message == "__VOICE_READY__":
                    self.log("Voice input ready. Say a protocol name or number.")
                elif message.startswith("__VOICE_ERROR__"):
                    self.log(f"Voice input failed: {message.removeprefix('__VOICE_ERROR__')}")
                elif message == _CANCEL_COMMAND:
                    self.on_command("cancel")
                elif message:
                    self.on_command(message)
        finally:
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError as exc:
                    self.log(f"Voice input stop failed: {exc}")
            process.wait()
            with self._lock:
                if self._process is process:
                    self._process = None
            if not self._stopping.is_set() and process.returncode:
                self.log(f"Voice input stopped unexpectedly (exit {process.returncode}).")
