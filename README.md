# Tactical Ops Console

A Windows desktop dashboard for system protocols, with global hotkeys, offline
voice control, and simulation mode.

## Run

Requires Windows and Python 3.10 or later:

```powershell
pip install -r requirements.txt
python main.py
```

Use the command field or protocol list to run actions. Type `help` in the
command field for available commands. Voice control and hotkeys can be
configured in the app.

## Safety

The default `config.json` enables simulation mode and disables destructive
actions. Review the configuration before enabling live actions. Some global
hotkeys may require elevated permissions.

## Build

Download the latest Windows executable from [Releases](https://github.com/HitchItIs/expert-adventure/releases).
Changes to the app or its dependencies build a test artifact; version tags
publish a release.

## To-do

- Fix voice input after locking and unlocking Windows.
- Add commands and make them easier to extend.
- Add secure voice confirmation for destructive actions.
- Improve reliable background operation.
- Save diagnostic logs as JSON.
