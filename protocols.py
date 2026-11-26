import os
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PROTECTED_PROCESSES = {
    "applicationframehost.exe",
    "audiodg.exe",
    "backgroundtaskhost.exe",
    "conhost.exe",
    "csrss.exe",
    "ctfmon.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "lsass.exe",
    "lockapp.exe",
    "runtimebroker.exe",
    "searchhost.exe",
    "services.exe",
    "smss.exe",
    "startmenuexperiencehost.exe",
    "svchost.exe",
    "system",
    "system idle process",
    "taskhostw.exe",
    "textinputhost.exe",
    "win32webviewhost.exe",
    "wininit.exe",
    "winlogon.exe",
    "widgets.exe",
}


@dataclass(frozen=True)
class Protocol:
    code: str
    name: str
    alias: str
    number: str
    description: str
    voice_line: str


PROTOCOLS = (
    Protocol("KD-101", "Kilo-Delta-101", "kilo-delta-101", "1", "Lockdown — clear clipboard and lock PC", "Kilo-Delta-101 bestätigt. System verriegelt."),
    Protocol("EZ-404", "Echo-Zero-404", "echo-zero-404", "2", "Ghost — close eligible user apps", "Echo-Zero-404 ausgeführt."),
    Protocol("AO-07", "Alpha-Oscar-07", "alpha-oscar-07", "3", "Launch — open configured apps and URLs", "Alpha-Oscar-07 ausgeführt."),
    Protocol("B6-00", "Bravo-Six-00", "bravo-six-00", "4", "Blackout — mute, dim screen, and lock", "Bravo-Six-00. Going dark."),
    Protocol("TM-24", "Tango-Mirage-24", "tango-mirage-24", "5", "Decoy — minimize windows and open URL", "Tango-Mirage-24 ausgeführt."),
    Protocol("CV-99", "Charlie-Victor-99", "charlie-victor-99", "6", "Nuke — clear temp/recent items and clipboard", "Charlie-Victor-99 ausgeführt."),
    Protocol("VD-55", "Viper-Delta-55", "viper-delta-55", "7", "Gaming Mode — stop apps; select performance plan", "Viper-Delta-55 aktiviert."),
    Protocol("NE-23", "November-Echo-23", "november-echo-23", "8", "Night Mode — dim screen, lower volume, optional timer", "November-Echo-23 aktiviert."),
    Protocol("SD-883", "Sierra-Delta-883", "sierra-delta-883", "9", "Flush — flush DNS, restart Explorer, report RAM", "Sierra-Delta-883 ausgeführt. System bereinigt."),
    Protocol("RK-303", "Romeo-Kilo-303", "romeo-kilo-303", "0", "Diagnostics — show CPU, memory, disk, network", "Romeo-Kilo-303: Diagnose abgeschlossen."),
    Protocol("OZ-000", "Omega-Zulu-000", "omega-zulu-000", "backspace", "Countdown — cancel with Esc or 'cancel'; then lock", "Omega-Zulu-000 sequence complete."),
)
PROTOCOLS_BY_CODE = {protocol.code: protocol for protocol in PROTOCOLS}


def resolve_protocol(value):
    normalized = str(value).strip().casefold()
    for protocol in PROTOCOLS:
        if normalized in {
            protocol.code.casefold(),
            protocol.name.casefold(),
            protocol.alias.casefold(),
            protocol.number.casefold(),
        }:
            return protocol
    return None


class ProtocolRunner:
    def __init__(self, config, log, voice):
        self.config = config
        self.log = log
        self.voice = voice
        self._shutdown_timer = None
        self._shutdown_timer_lock = threading.Lock()
        self._cancel_countdown = threading.Event()

    def start(self, value):
        protocol = resolve_protocol(value)
        if protocol is None:
            self.log(f"Unknown protocol: {value}")
            return None
        thread = threading.Thread(target=self.execute, args=(protocol,), daemon=True)
        thread.start()
        return thread

    def execute(self, protocol):
        self.log(f"{protocol.code}: {protocol.description} sequence started.")
        handlers = {
            "KD-101": self.lockdown,
            "EZ-404": self.ghost,
            "AO-07": self.launch,
            "B6-00": self.blackout,
            "TM-24": self.decoy,
            "CV-99": self.nuke,
            "VD-55": self.gaming_mode,
            "NE-23": self.night_mode,
            "SD-883": self.flush,
            "RK-303": self.diagnostics,
            "OZ-000": self.self_destruct,
        }
        try:
            result = handlers[protocol.code]()
            if result is False:
                self.log(f"{protocol.code}: sequence cancelled.")
                return
            self.voice.say(protocol.voice_line)
            self.log(f"{protocol.code}: sequence complete.")
        except Exception as exc:
            self.log(f"{protocol.code}: operation failed: {exc}")

    def cancel(self):
        self._cancel_countdown.set()
        with self._shutdown_timer_lock:
            timer = self._shutdown_timer
            if timer is not None:
                timer.cancel()
                self._shutdown_timer = None
                self.log("Shutdown timer cancelled.")

    def _allowed(self):
        return bool(self.config.get("allow_destructive_actions", False))

    def _perform(self, description, action, destructive=True):
        if self.config.get("test_mode", True):
            self.log(f"TEST MODE: simulated — {description}")
            return None
        if destructive and not self._allowed():
            self.log(f"Blocked: enable allow_destructive_actions to run — {description}")
            return None
        if os.name != "nt":
            self.log(f"Skipped (Windows only): {description}")
            return None
        action()
        self.log(description)
        return True

    @staticmethod
    def _windows():
        if os.name != "nt":
            raise OSError("This operation requires Windows.")

    @staticmethod
    def _command(args, **kwargs):
        return subprocess.run(
            args,
            check=False,
            timeout=30,
            creationflags=CREATE_NO_WINDOW,
            **kwargs,
        )

    def _lock_workstation(self):
        self._windows()
        import ctypes

        if not ctypes.windll.user32.LockWorkStation():
            raise OSError("Windows refused the workstation lock request.")

    def _clear_clipboard(self):
        self._windows()
        result = self._command(["clip"], input="", text=True, capture_output=True)
        if result.returncode:
            raise OSError(result.stderr.strip() or "Could not clear the clipboard.")

    def lockdown(self):
        self._perform("Clipboard cleared.", self._clear_clipboard)
        self._perform("Workstation locked.", self._lock_workstation, destructive=False)

    def ghost(self):
        try:
            import psutil
        except ImportError as exc:
            raise RuntimeError("Install psutil to use Ghost.") from exc
        whitelist = {name.casefold() for name in self.config.get("whitelist", [])}
        current_user = psutil.Process().username().casefold()
        current_pid = os.getpid()
        system_root = os.environ.get("SystemRoot", r"C:\Windows").casefold().rstrip("\\/")

        def terminate_user_apps():
            self._windows()
            import ctypes
            from ctypes import wintypes

            visible_pids = set()

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def visit_window(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd) and ctypes.windll.user32.GetWindowTextLengthW(hwnd):
                    pid = wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    visible_pids.add(pid.value)
                return True

            ctypes.windll.user32.EnumWindows(visit_window, 0)
            for process in psutil.process_iter(["pid", "name", "username", "exe"]):
                try:
                    name = (process.info["name"] or "").casefold()
                    username = (process.info["username"] or "").casefold()
                    executable = (process.info["exe"] or "").casefold()
                    if (
                        process.info["pid"] != current_pid
                        and process.info["pid"] in visible_pids
                        and username == current_user
                        and name not in PROTECTED_PROCESSES
                        and name not in whitelist
                        and not executable.startswith(system_root + "\\")
                    ):
                        process.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        self._perform("Eligible user applications terminated.", terminate_user_apps)

    def launch(self):
        apps = self.config.get("apps", [])
        urls = self.config.get("urls", [])
        if not apps and not urls:
            self.log("No apps or URLs configured.")
            return

        def open_targets():
            for app in apps:
                if os.name == "nt":
                    os.startfile(os.path.expandvars(app))
                else:
                    subprocess.Popen([app])
            for url in urls:
                webbrowser.open(url)

        self._perform(f"Launching {len(apps)} app(s) and {len(urls)} URL(s).", open_targets, destructive=False)

    @staticmethod
    def _set_monitor_power(standby):
        ProtocolRunner._windows()
        import ctypes

        command = 0x0112
        state = 2 if standby else -1
        ctypes.windll.user32.SendMessageW(0xFFFF, command, 0xF170, state)

    @staticmethod
    def _press_key(key):
        ProtocolRunner._windows()
        import ctypes

        ctypes.windll.user32.keybd_event(key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key, 0, 2, 0)

    def blackout(self):
        self._perform("Monitor placed in standby.", lambda: self._set_monitor_power(True))
        self._perform("System audio muted.", lambda: self._press_key(0xAD))
        self._perform("Workstation locked.", self._lock_workstation)

    def decoy(self):
        url = self.config.get("decoy_url", "")

        def minimize_and_open():
            self._windows()
            import ctypes

            keybd_event = ctypes.windll.user32.keybd_event
            keybd_event(0x5B, 0, 0, 0)
            keybd_event(0x44, 0, 0, 0)
            keybd_event(0x44, 0, 2, 0)
            keybd_event(0x5B, 0, 2, 0)
            if url:
                webbrowser.open(url)

        self._perform("Windows minimized and decoy opened.", minimize_and_open, destructive=False)

    @staticmethod
    def _remove_children(directory):
        root = Path(directory)
        if not root.is_dir():
            return 0
        removed = 0
        for child in root.iterdir():
            try:
                if child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
            except (OSError, PermissionError):
                continue
        return removed

    def nuke(self):
        def clean():
            self._windows()
            temp = Path(os.environ["TEMP"]).resolve()
            recent = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Recent"
            recent = recent.resolve()
            deleted_temp = self._remove_children(temp)
            deleted_recent = self._remove_children(recent)
            self.log(f"Removed {deleted_temp} TEMP item(s) and {deleted_recent} Recent item(s).")

        self._perform("TEMP and Recent folders cleaned.", clean)
        self._perform("Clipboard cleared.", self._clear_clipboard)

    def gaming_mode(self):
        try:
            import psutil
        except ImportError as exc:
            raise RuntimeError("Install psutil to use Gaming Mode.") from exc
        targets = {name.casefold() for name in self.config.get("gaming_processes", [])}

        def optimize():
            for process in psutil.process_iter(["name"]):
                try:
                    if (process.info["name"] or "").casefold() in targets:
                        process.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            result = self._command(["powercfg", "/setactive", "SCHEME_MAX"])
            if result.returncode:
                raise OSError("powercfg could not enable the high-performance plan.")

        self._perform("Configured background apps stopped; high-performance plan selected.", optimize)

    def night_mode(self):
        def dim_and_reduce_volume():
            self._windows()
            try:
                import screen_brightness_control

                screen_brightness_control.set_brightness(int(self.config.get("brightness_percent", 30)))
            except Exception as exc:
                self.log(f"Brightness control unavailable; continuing with volume: {exc}")
            for _ in range(5):
                self._press_key(0xAE)

        self._perform("Brightness and volume reduced.", dim_and_reduce_volume)
        seconds = max(0, int(self.config.get("shutdown_timer_seconds", 0)))
        if not seconds:
            return
        if self.config.get("test_mode", True):
            self.log(f"TEST MODE: simulated — shutdown timer ({seconds}s).")
            return
        if not self._allowed() or os.name != "nt":
            self.log("Shutdown timer blocked by the safety settings or platform.")
            return
        timer = threading.Timer(seconds, self._shutdown_now)
        timer.daemon = True
        with self._shutdown_timer_lock:
            if self._shutdown_timer is not None:
                self._shutdown_timer.cancel()
            self._shutdown_timer = timer
            timer.start()
        self.log(f"Shutdown scheduled in {seconds}s. Enter 'cancel' to abort.")

    def _shutdown_now(self):
        with self._shutdown_timer_lock:
            if self._shutdown_timer is not threading.current_thread():
                return
            self._shutdown_timer = None
        self._perform("Shutdown timer expired; shutting down.", lambda: self._command(["shutdown", "/s", "/t", "0"]))

    def flush(self):
        def flush_dns():
            result = self._command(["ipconfig", "/flushdns"])
            if result.returncode:
                raise OSError("DNS cache flush failed.")

        def restart_explorer():
            import psutil

            for process in psutil.process_iter(["name"]):
                try:
                    if (process.info["name"] or "").casefold() == "explorer.exe":
                        process.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            subprocess.Popen(["explorer.exe"], creationflags=CREATE_NO_WINDOW)

        self._perform("DNS cache flushed.", flush_dns)
        self._perform("Explorer restarted.", restart_explorer)
        try:
            import psutil

            free_memory = psutil.virtual_memory().available / (1024**3)
            self.log(f"Available RAM: {free_memory:.1f} GiB.")
        except ImportError:
            self.log("RAM status unavailable: install psutil.")

    def diagnostics(self):
        if self.config.get("test_mode", True):
            self.log("TEST MODE: simulated — CPU, memory, disk, IP, and connectivity report.")
            return
        try:
            import psutil
        except ImportError as exc:
            raise RuntimeError("Install psutil to run diagnostics.") from exc

        cpu = psutil.cpu_percent(interval=0.25)
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage(Path.home())
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            local_ip = "unavailable"
        ping_args = ["ping", "-n", "1", "-w", "1000", "1.1.1.1"] if os.name == "nt" else ["ping", "-c", "1", "-W", "1", "1.1.1.1"]
        ping = subprocess.run(ping_args, check=False, capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        self.log(
            f"CPU {cpu:.0f}% | RAM {memory.percent:.0f}% | Free disk {disk.free / (1024**3):.1f} GiB "
            f"| IP {local_ip} | Ping {'online' if ping.returncode == 0 else 'unavailable'}."
        )

    def self_destruct(self):
        self._cancel_countdown.clear()
        remove_escape = None
        try:
            if os.name == "nt":
                import keyboard

                remove_escape = keyboard.add_hotkey("esc", self._cancel_countdown.set, suppress=False)
        except (ImportError, OSError):
            self.log("ESC hook unavailable; enter 'cancel' to abort.")

        try:
            for remaining in range(10, -1, -1):
                if self._cancel_countdown.is_set():
                    self.log("Countdown aborted.")
                    self.voice.say("Omega-Zulu-000 abgebrochen.")
                    return False
                self.log(f"OMEGA-ZULU-000: {remaining}")
                self.voice.say(str(remaining))
                if remaining:
                    time.sleep(1)
            self._perform("Countdown complete; workstation locked.", self._lock_workstation)
            return True
        finally:
            if remove_escape is not None:
                try:
                    import keyboard

                    keyboard.remove_hotkey(remove_escape)
                except (ImportError, KeyError):
                    pass
