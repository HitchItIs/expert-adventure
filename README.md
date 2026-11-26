# TACTICAL OPS CONSOLE

A Windows desktop dashboard with 11 protocols, configurable global hotkeys,
offline speech, and a simulation-first mode.

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

Use the protocol list or command field to run a code, alias, or number. The
**Hotkey settings** button opens the shortcut editor; **Cancel timer /
countdown** and **Exit** remain available in the window. **Test voice** checks
speech output. When **Voice I/O** is enabled, the app also listens for protocol
names, action names, numbers, and the `cancel` command using Windows' built-in
speech recognition; recognition stays on the computer. Voice errors are shown
in the radio log. Global keyboard hooks may require elevated permissions on
Windows.

## Build

The latest Windows executable is published as a downloadable asset on the
repository's [Releases page](https://github.com/HitchItIs/expert-adventure/releases).
Each `v*` version tag builds and publishes `TacticalOpsConsole.exe` and the
default `config.json`. To publish an existing tag manually, open **Actions →
Release Windows executable → Run workflow** and enter its tag. Keep the files
together; the executable also creates a default config beside itself if the
file is absent.

Every push to `main` that changes the application or its dependencies also
builds an Actions artifact for testing. To build on demand, open
**Actions → Build Windows executable → Run workflow**.

To build locally, use Windows (PyInstaller does not cross-compile Windows
executables from Linux):

```powershell
pyinstaller --onefile --windowed --name TacticalOpsConsole --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 --collect-submodules comtypes --hidden-import keyboard main.py
```

The executable is written to `dist\TacticalOpsConsole.exe`. `config.json` is
read from or generated beside the executable on first start.
