# TACTICAL OPS CONSOLE

A Windows-oriented Rich dashboard with 11 desktop protocols, configurable global
hotkeys, offline speech, and a simulation-first mode.

## Safety and configuration

The included `config.json` starts with `test_mode: true` and
`allow_destructive_actions: false`. TEST MODE simulates protocol effects.
Changing to live mode alone does not permit destructive actions: explicitly set
`allow_destructive_actions` to `true` in `config.json` as well. Protocol hotkeys,
application launch targets, whitelist, brightness, and shutdown timer are also
configured there. Review those settings before enabling live actions.

Run on Windows with Python 3.10 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Use a protocol code, alias, or number in the terminal. Enter `test` to toggle
simulation mode, `cancel` to abort a shutdown/countdown, and `quit` to exit.
Global keyboard hooks may require elevated permissions on Windows.

## Build

Build the Windows executable on Windows (PyInstaller does not cross-compile
Windows executables from Linux):

```powershell
pyinstaller --onefile --name TacticalOpsConsole --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 --hidden-import keyboard --hidden-import rich main.py
```

The executable is written to `dist\TacticalOpsConsole.exe`. `config.json` is
read from or generated beside the executable on first start.
