import json
import queue
import sys
import threading
import time
from pathlib import Path

from rich import box
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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


def render_dashboard(config, logs):
    table = Table(box=box.SIMPLE, expand=True)
    table.add_column("Protocol", style="cyan")
    table.add_column("Code", style="green")
    table.add_column("Hotkey", style="yellow")
    table.add_column("Mission")
    for protocol in PROTOCOLS:
        table.add_row(
            protocol.name,
            protocol.code,
            str(config.get("hotkeys", {}).get(protocol.code, "—")),
            protocol.description,
        )

    mode = "TEST MODE" if config.get("test_mode", True) else "LIVE MODE"
    mode_style = "yellow" if config.get("test_mode", True) else "red"
    log_text = "\n".join(logs[-10:]) or "Awaiting input…"
    return Panel(
        Group(
            Text(mode, style=f"bold {mode_style}"),
            table,
            Text("RADIO LOG", style="bold cyan"),
            Text(log_text),
            Text("Enter code, full name, or number | settings | test | cancel | help | quit", style="dim"),
        ),
        title="[bold green]TACTICAL OPS CONSOLE[/bold green]",
        border_style="cyan",
    )


def _read_commands(command_queue):
    while True:
        try:
            command = input("ops> ").strip()
        except EOFError:
            command = "quit"
        command_queue.put(command)
        if command.casefold() in {"quit", "exit"}:
            return


def main():
    from rich.console import Console

    console = Console()
    config_path = get_base_dir() / "config.json"
    config = load_config(config_path)
    logs = queue.Queue()
    visible_logs = []
    voice = Voice(config.get("voice_enabled", True))
    runner = ProtocolRunner(config, logs.put, voice)
    commands = queue.Queue()
    stop = threading.Event()

    def activate(value):
        runner.start(value)

    def toggle_test_mode():
        config["test_mode"] = not config.get("test_mode", True)
        save_config(config, config_path)
        logs.put(f"TEST MODE {'enabled' if config['test_mode'] else 'disabled'}.")

    hotkeys = Hotkeys(config, activate, toggle_test_mode)
    try:
        hotkeys.start()
        logs.put("Global hotkeys registered.")
    except RuntimeError as exc:
        logs.put(f"Global hotkeys unavailable: {exc}")

    threading.Thread(target=_read_commands, args=(commands,), daemon=True).start()
    try:
        with Live(render_dashboard(config, visible_logs), refresh_per_second=4, console=console) as live:
            while not stop.is_set():
                changed = False
                while True:
                    try:
                        visible_logs.append(logs.get_nowait())
                        changed = True
                    except queue.Empty:
                        break
                while True:
                    try:
                        command = commands.get_nowait()
                    except queue.Empty:
                        break
                    lowered = command.casefold()
                    if lowered in {"quit", "exit"}:
                        stop.set()
                        break
                    if lowered == "settings":
                        hotkeys.stop()
                        try:
                            if configure_hotkeys(config, config_path, save_config):
                                logs.put("Hotkey settings saved.")
                            else:
                                logs.put("Hotkey settings unchanged.")
                        except RuntimeError as exc:
                            logs.put(str(exc))
                        try:
                            hotkeys.start()
                            logs.put("Global hotkeys registered.")
                        except RuntimeError as exc:
                            logs.put(f"Global hotkeys unavailable: {exc}")
                    elif lowered == "test":
                        toggle_test_mode()
                    elif lowered == "cancel":
                        runner.cancel()
                    elif lowered == "help":
                        logs.put("Use a protocol code, alias, or number. 'test' toggles simulation; 'cancel' aborts timers.")
                    else:
                        protocol = resolve_protocol(command)
                        if protocol:
                            runner.start(protocol.code)
                        elif command:
                            logs.put(f"Unknown command: {command}")
                    changed = True
                if changed:
                    live.update(render_dashboard(config, visible_logs))
                time.sleep(0.1)
    except KeyboardInterrupt:
        stop.set()
    finally:
        hotkeys.stop()
        runner.cancel()


if __name__ == "__main__":
    main()
