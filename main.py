import json
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from hotkeys import Hotkeys
from hotkey_settings import configure_hotkeys
from protocols import PROTOCOLS, ProtocolRunner, resolve_protocol
from voice import Voice


DEFAULT_HOTKEYS = {
    "KD-101": "ctrl+alt+1",
    "EZ-404": "ctrl+alt+2",
    "AO-07": "ctrl+alt+3",
    "B6-00": "ctrl+alt+4",
    "TM-24": "ctrl+alt+5",
    "CV-99": "ctrl+alt+6",
    "VD-55": "ctrl+alt+7",
    "NE-23": "ctrl+alt+8",
    "SD-883": "ctrl+alt+9",
    "RK-303": "ctrl+alt+0",
    "OZ-000": "ctrl+alt+backspace",
    "TEST": "ctrl+alt+t",
}


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_config():
    return {
        "test_mode": True,
        "allow_destructive_actions": False,
        "voice_enabled": True,
        "hotkeys": DEFAULT_HOTKEYS.copy(),
        "whitelist": ["Code.exe", "WindowsTerminal.exe", "explorer.exe"],
        "apps": [],
        "urls": [],
        "decoy_url": "",
        "gaming_processes": [],
        "brightness_percent": 30,
        "shutdown_timer_seconds": 0,
    }


def load_config(path=None):
    config_path = Path(path) if path else get_base_dir() / "config.json"
    defaults = default_config()
    if not config_path.exists():
        config_path.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
        return defaults
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{config_path} must contain a JSON object.")
    defaults.update(loaded)
    return defaults


def save_config(config, path=None):
    config_path = Path(path) if path else get_base_dir() / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


class TacticalOpsApp:
    def __init__(self, root, config, config_path):
        self.root = root
        self.config = config
        self.config_path = config_path
        self.logs = queue.Queue()
        self.ui_events = queue.Queue()
        self.closing = False
        self.voice = Voice(config.get("voice_enabled", True), self.logs.put)
        self.runner = ProtocolRunner(config, self.logs.put, self.voice)
        self.hotkeys = Hotkeys(
            config,
            self.runner.start,
            lambda: self.ui_events.put("toggle_test_mode"),
        )

        self.root.title("Tactical Ops Console")
        self.root.geometry("1020x740")
        self.root.minsize(780, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.report_callback_exception = self._report_callback_exception

        try:
            self.hotkeys.start()
            self.logs.put("Global hotkeys registered.")
        except RuntimeError as exc:
            self.logs.put(f"Global hotkeys unavailable: {exc}")

        self.logs.put("Ready. TEST MODE is on; actions are simulated.")
        self.root.after(100, self._drain_logs)
        self.root.after(150, self.command_entry.focus_set)

    def _build_ui(self):
        style = ttk.Style(self.root)
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Mode.TLabel", font=("Segoe UI", 10, "bold"))

        container = ttk.Frame(self.root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)
        container.rowconfigure(5, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="TACTICAL OPS CONSOLE", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.mode_label = ttk.Label(header, style="Mode.TLabel")
        self.mode_label.grid(row=0, column=1, padx=(12, 0), sticky="e")
        self._update_mode_label()

        toolbar = ttk.Frame(container)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, text="Protocols").grid(row=0, column=0, sticky="w")
        ttk.Button(toolbar, text="Change mode", command=self.toggle_test_mode).grid(
            row=0, column=1, padx=(8, 0)
        )

        protocol_frame = ttk.Frame(container)
        protocol_frame.grid(row=2, column=0, sticky="nsew")
        protocol_frame.columnconfigure(0, weight=1)
        protocol_frame.rowconfigure(0, weight=1)
        columns = ("name", "code", "hotkey", "description")
        self.protocol_table = ttk.Treeview(
            protocol_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=9,
        )
        self.protocol_table.heading("name", text="Protocol")
        self.protocol_table.heading("code", text="Code")
        self.protocol_table.heading("hotkey", text="Global shortcut")
        self.protocol_table.heading("description", text="Action")
        self.protocol_table.column("name", width=210, minwidth=150)
        self.protocol_table.column("code", width=110, minwidth=90, stretch=False)
        self.protocol_table.column("hotkey", width=180, minwidth=140)
        self.protocol_table.column("description", width=220, minwidth=150)
        self.protocol_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            protocol_frame,
            orient="vertical",
            command=self.protocol_table.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.protocol_table.configure(yscrollcommand=scrollbar.set)
        self.protocol_table.bind("<Double-1>", lambda _: self.run_selected())
        self._populate_protocol_table()

        actions = ttk.Frame(container)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 12))
        ttk.Button(actions, text="Run selected", command=self.run_selected).pack(
            side="left"
        )
        ttk.Button(actions, text="Cancel timer / countdown", command=self.cancel).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Hotkey settings…", command=self.open_settings).pack(
            side="left", padx=(8, 0)
        )
        self.voice_enabled = tk.BooleanVar(value=self.voice.enabled)
        ttk.Checkbutton(
            actions,
            text="Voice",
            variable=self.voice_enabled,
            command=self.set_voice_enabled,
        ).pack(side="left", padx=(16, 0))
        ttk.Button(actions, text="Test voice", command=self.test_voice).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Exit", command=self.close).pack(side="right")

        command_frame = ttk.Frame(container)
        command_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        command_frame.columnconfigure(1, weight=1)
        ttk.Label(command_frame, text="Command").grid(row=0, column=0, padx=(0, 8))
        self.command_value = tk.StringVar()
        self.command_entry = ttk.Entry(command_frame, textvariable=self.command_value)
        self.command_entry.grid(row=0, column=1, sticky="ew")
        self.command_entry.bind("<Return>", self.submit_command)
        ttk.Button(command_frame, text="Run", command=self.submit_command).grid(
            row=0, column=2, padx=(8, 0)
        )

        log_frame = ttk.LabelFrame(container, text="Radio log", padding=8)
        log_frame.grid(row=5, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_view = scrolledtext.ScrolledText(
            log_frame,
            wrap="word",
            state="disabled",
            height=10,
            font=("Consolas", 10),
        )
        self.log_view.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            container,
            text="Enter a protocol code, name, or number. Commands: test, cancel, help, quit.",
        ).grid(row=6, column=0, sticky="w", pady=(8, 0))

    def _populate_protocol_table(self):
        self.protocol_table.delete(*self.protocol_table.get_children())
        hotkeys = self.config.get("hotkeys", {})
        for protocol in PROTOCOLS:
            self.protocol_table.insert(
                "",
                "end",
                iid=protocol.code,
                values=(
                    protocol.name,
                    protocol.code,
                    hotkeys.get(protocol.code, ""),
                    protocol.description,
                ),
            )

    def _update_mode_label(self):
        if self.config.get("test_mode", True):
            self.mode_label.configure(text="TEST MODE — simulated", foreground="#8a6500")
        else:
            self.mode_label.configure(text="LIVE MODE", foreground="#b00020")

    def _drain_logs(self):
        if self.closing:
            return
        while True:
            try:
                event = self.ui_events.get_nowait()
            except queue.Empty:
                break
            if event == "toggle_test_mode":
                self.toggle_test_mode()

        messages = []
        while True:
            try:
                messages.append(self.logs.get_nowait())
            except queue.Empty:
                break
        if messages:
            self.log_view.configure(state="normal")
            for message in messages:
                self.log_view.insert("end", f"{message}\n")
            line_count = int(self.log_view.index("end-1c").split(".")[0])
            if line_count > 500:
                self.log_view.delete("1.0", f"{line_count - 500}.0")
            self.log_view.see("end")
            self.log_view.configure(state="disabled")
        self.root.after(100, self._drain_logs)

    def run_selected(self):
        selected = self.protocol_table.selection()
        if not selected:
            self.logs.put("Select a protocol or enter its code, name, or number.")
            return
        self.runner.start(selected[0])

    def submit_command(self, _event=None):
        command = self.command_value.get().strip()
        self.command_value.set("")
        if not command:
            return "break"
        lowered = command.casefold()
        if lowered in {"quit", "exit"}:
            self.close()
        elif lowered == "test":
            self.toggle_test_mode()
        elif lowered == "cancel":
            self.cancel()
        elif lowered == "settings":
            self.open_settings()
        elif lowered == "help":
            self.logs.put(
                "Choose a protocol or enter its code, name, or number. "
                "Use Cancel timer / countdown to abort an active sequence."
            )
        else:
            protocol = resolve_protocol(command)
            if protocol:
                self.runner.start(protocol.code)
            else:
                self.logs.put(f"Unknown command: {command}")
        return "break"

    def toggle_test_mode(self):
        current = bool(self.config.get("test_mode", True))
        if current and not messagebox.askyesno(
            "Enable live mode?",
            "Live mode can perform real actions on this computer. "
            "Destructive actions remain blocked unless separately enabled. Continue?",
            parent=self.root,
        ):
            return

        self.config["test_mode"] = not current
        try:
            save_config(self.config, self.config_path)
        except OSError as exc:
            self.config["test_mode"] = current
            messagebox.showerror("Could not save settings", str(exc), parent=self.root)
            return
        self._update_mode_label()
        self.logs.put(f"{'TEST' if self.config['test_mode'] else 'LIVE'} MODE enabled.")

    def cancel(self):
        self.runner.cancel()
        self.logs.put("Cancel requested.")

    def open_settings(self):
        self.hotkeys.stop()
        try:
            saved = configure_hotkeys(
                self.config,
                self.config_path,
                save_config,
                parent=self.root,
            )
            self.logs.put(
                "Hotkey settings saved." if saved else "Hotkey settings unchanged."
            )
        except RuntimeError as exc:
            self.logs.put(str(exc))
        finally:
            self._populate_protocol_table()
            try:
                self.hotkeys.start()
                self.logs.put("Global hotkeys registered.")
            except RuntimeError as exc:
                self.logs.put(f"Global hotkeys unavailable: {exc}")

    def set_voice_enabled(self):
        previous = bool(self.config.get("voice_enabled", True))
        enabled = self.voice_enabled.get()
        self.config["voice_enabled"] = enabled
        self.voice.set_enabled(enabled)
        try:
            save_config(self.config, self.config_path)
        except OSError as exc:
            self.config["voice_enabled"] = previous
            self.voice.set_enabled(previous)
            self.voice_enabled.set(previous)
            messagebox.showerror("Could not save settings", str(exc), parent=self.root)
            return
        self.logs.put(f"Voice output {'enabled' if enabled else 'disabled'}.")

    def test_voice(self):
        if not self.voice.say("Voice output test."):
            self.logs.put("Voice output is disabled.")
        else:
            self.logs.put("Voice test requested.")

    def _report_callback_exception(self, exception, value, traceback):
        self.logs.put(f"UI error: {value}")

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.hotkeys.stop()
        self.runner.cancel()
        self.voice.close()
        self.root.destroy()


def main():
    config_path = get_base_dir() / "config.json"
    config = load_config(config_path)
    root = tk.Tk()
    TacticalOpsApp(root, config, config_path)
    root.mainloop()


if __name__ == "__main__":
    main()
