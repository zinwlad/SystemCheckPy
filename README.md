# SystemCheckPy

Windows system diagnostic tool with GUI (PyQt5) and CLI.

## Features
- Cancelable command execution with timeout
- Streamed output for long-running commands (e.g., SFC, DISM)
- Detailed results (stdout, stderr, return code)
- Search/filter commands + Favorites (persistent)
- Logs with daily rotation in `logs/` (cp1251)
- Theme toggle (light/dark), persistent via QSettings
- Open logs folder button
- UAC prompt for admin-required commands
- Modern PowerShell commands (Get-CimInstance, Get-Package)

## Install
1) Python 3.10+
2) Install deps:
```
pip install -r requirements.txt
```

## Run (GUI)
```
python main.py
```
If a command requires admin rights, the app will offer to restart elevated.

## Run (CLI)
```
python SystemCheckPy.py
```

## Logs
- Stored in `logs/log_YYYYMMDD.txt`
- Daily rotation, keep 7 days
- Encoding cp1251 (better for Russian Windows)

## Settings
- Stored via QSettings under `SystemCheckPy/SystemCheckPyApp`
- Persisted: theme (dark/light), timeout, favorites

## Streaming output
- For: "Проверить целостность системных файлов", "Выполнить CHKDSK", "Выполнить DISM"
- Output appears in real-time; timeout auto-raised to at least 30 minutes for these

## Favorites & Search
- Use the search field above the command list
- Toggle favorite with the ☆/★ button or Ctrl+D
- Filter only favorites with the checkbox

## Keyboard Shortcuts
- Ctrl+Enter: Execute
- Ctrl+F: Focus search
- Ctrl+D: Toggle favorite
- Ctrl+L: Open logs folder
- Esc: Cancel running command
- Ctrl+T: Toggle theme

## Adding/Editing Commands
- Commands live in `commands.py` as a dict: name -> { description, command, requires_admin? }
- Prefer CIM over WMI (Get-CimInstance)
- Mark admin-required commands with `"requires_admin": true`

## Known Notes
- Some commands rely on external tools (e.g., `speedtest-cli`, `nvidia-smi`). Install them if needed.
- Encoding: GUI tries utf-8, cp1251, cp866 when viewing logs.

## Contributing
- PRs and issues welcome. Keep commands safe and fast.
