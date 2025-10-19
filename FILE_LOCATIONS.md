# TermoLoad - File Locations Guide

## Log File Location

### Primary Log File
**Location**: `%USERPROFILE%\termoload.log`

**Full Path Examples**:
- `C:\Users\YourUsername\termoload.log`
- For user "adhdh": `C:\Users\adhdh\termoload.log`

**How to Find It**:
1. Open File Explorer
2. Type `%USERPROFILE%` in the address bar
3. Look for `termoload.log` in your user folder

**Or via Terminal**:
```powershell
# View the log file location
echo $env:USERPROFILE\termoload.log

# Open the log file
notepad $env:USERPROFILE\termoload.log

# View last 50 lines
Get-Content $env:USERPROFILE\termoload.log -Tail 50
```

### What's Logged
- App startup and initialization
- Download operations (start, progress, completion, errors)
- Torrent session events
- File dialog operations
- Error messages and exceptions
- System tray events

---

## Download History File

**Location**: `%USERPROFILE%\.termoload_history.json`

**Full Path Example**: `C:\Users\YourUsername\.termoload_history.json`

**Contents**: JSON database of all download attempts with:
- Download date/time
- File names and URLs
- Download status (completed/failed/cancelled)
- File sizes
- Error messages (if any)

---

## Settings File

**Location**: `{app_directory}\settings.json`

**Default Path**: Same folder as the executable or `app.py`

**Contents**:
- Default download folder
- Concurrent download limit
- Speed limit settings
- Sound notification preferences

---

## Downloads State File

**Location**: `{app_directory}\downloads_state.json`

**Contents**: Active/paused download queue for resume on restart

---

## Default Download Folder

**NEW Default**: `C:\Users\{YourUsername}\Downloads`

**Previous Default**: `{app_directory}\downloads`

**Why Changed**: 
- Standard Windows location for downloads
- Easier to find downloaded files
- Consistent with other download managers

**How to Change**:
1. Open TermoLoad
2. Press `s` for Settings
3. Update "Download Folder" field
4. Click "Save Settings"

---

## Quick Access Commands

### View Log File
```powershell
notepad %USERPROFILE%\termoload.log
```

### Open Downloads Folder
```powershell
explorer %USERPROFILE%\Downloads
```

### View History
```powershell
notepad %USERPROFILE%\.termoload_history.json
```

### Check Settings
```powershell
notepad settings.json
```

---

## Troubleshooting

### Can't Find Log File?
Run in PowerShell:
```powershell
Test-Path "$env:USERPROFILE\termoload.log"
```
If returns `False`, the log hasn't been created yet (app hasn't run).

### Log File Too Large?
```powershell
# Check size
(Get-Item $env:USERPROFILE\termoload.log).length / 1MB

# Clear old log (backup first)
Copy-Item $env:USERPROFILE\termoload.log $env:USERPROFILE\termoload_backup.log
Clear-Content $env:USERPROFILE\termoload.log
```

### Change Download Location?
1. Settings tab in TermoLoad
2. Or edit `settings.json` directly:
```json
{
  "download_folder": "D:\\MyDownloads"
}
```

---

## File Summary Table

| File | Location | Purpose |
|------|----------|---------|
| `termoload.log` | `%USERPROFILE%\` | Application logs |
| `.termoload_history.json` | `%USERPROFILE%\` | Download history database |
| `settings.json` | App directory | User preferences |
| `downloads_state.json` | App directory | Active download queue |
| Downloaded files | `%USERPROFILE%\Downloads` | Your downloaded content |

---

## Notes

- Log file rotates automatically when it gets too large
- History file grows with each download (can be exported to CSV)
- Settings file is created on first run
- All paths use Windows-style backslashes internally
- The app creates directories automatically if they don't exist
