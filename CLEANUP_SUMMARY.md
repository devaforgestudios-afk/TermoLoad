# Cleanup & Configuration Changes - v2.1

**Date**: October 20, 2025

---

## ✅ Changes Made

### 1. Cleaned Up Unnecessary Files

**Deleted**:
- `__pycache__/` - Python bytecode cache
- `build/` - PyInstaller build artifacts
- `build_exe_fast.bat` - Duplicate build script
- `build_exe_fast.spec` - Duplicate spec file
- `TermoLoad.spec` - Auto-generated spec (kept build_exe.spec)
- `BUILD_OPTIMIZATION.md` - Duplicate docs
- `OPTIMIZATION_COMPLETE.md` - Duplicate docs
- `OPTIMIZATION_NOTES.md` - Duplicate docs
- `EXE_FIX_NOTES.md` - Duplicate docs

**Kept**:
- `build_exe.bat` - Main build script (updated)
- `build_exe.spec` - Main spec file
- `build_fast.bat` - Fast onedir/console build script
- `BUILD_SUMMARY.md` - Build documentation
- `OPTIMIZATION_SUMMARY.md` - Optimization notes
- `FILE_LOCATIONS.md` - NEW: File locations guide

---

### 2. Changed Default Download Path

**Old Default**: `{app_directory}\downloads`  
**New Default**: `C:\Users\{username}\Downloads`

**Why**: 
- Standard Windows location
- Users expect downloads here
- Easier to find files
- Consistent with other apps

**Code Changes**:
```python
# In load_settings():
windows_downloads = Path.home() / "Downloads"
default_download_path = str(windows_downloads)
```

**Affected Files**:
- All new downloads use Windows Downloads folder
- Existing downloads keep their original paths
- Settings can override this default

---

### 3. Documented File Locations

Created `FILE_LOCATIONS.md` with complete guide:

#### Log File
**Location**: `C:\Users\{YourUsername}\termoload.log`

**Quick Access**:
```powershell
notepad %USERPROFILE%\termoload.log
```

#### History File
**Location**: `C:\Users\{YourUsername}\.termoload_history.json`

#### Settings File
**Location**: `{app_directory}\settings.json`

#### Default Downloads
**Location**: `C:\Users\{YourUsername}\Downloads`

---

## 📁 Current Project Structure

```
E:\TermoLoad\
├── app.py                      # Main application
├── build_exe.bat               # Build script (supports args)
├── build_exe.spec              # PyInstaller spec
├── build_fast.bat              # Fast onedir build
├── requirements.txt            # Dependencies
├── settings.json               # User settings
├── downloads_state.json        # Download queue
├── dist/                       # Built executables
│   └── TermoLoad/
│       ├── TermoLoad.exe       # Main EXE (25.7 MB)
│       └── _internal/          # Dependencies
├── downloads/                  # Old default (legacy)
├── downloads_test/             # Test files
├── test/                       # Unit tests
├── README.md                   # Main documentation
├── BUILD_SUMMARY.md            # Build guide
├── OPTIMIZATION_SUMMARY.md     # Performance notes
└── FILE_LOCATIONS.md           # NEW: File locations guide
```

---

## 🎯 Log File Information

### Location
Your log file is at: `%USERPROFILE%\termoload.log`

### Real Path Examples
- For user "adhdh": `C:\Users\adhdh\termoload.log`
- For user "John": `C:\Users\John\termoload.log`

### View Log File
```powershell
# Open in Notepad
notepad %USERPROFILE%\termoload.log

# View last 50 lines in terminal
Get-Content $env:USERPROFILE\termoload.log -Tail 50

# Open log folder
explorer %USERPROFILE%
```

### What's Logged
- ✅ App startup/shutdown
- ✅ Download operations
- ✅ Torrent session events
- ✅ File dialog operations
- ✅ Errors and exceptions
- ✅ System tray events

---

## 🚀 Next Steps

### Test the Changes
```powershell
# Run the app
python app.py

# Check that downloads go to Windows Downloads folder
# Check that log file is created in %USERPROFILE%
```

### Rebuild EXE
```powershell
# Fast build (onedir + console)
.\build_fast.bat onedir console

# Standard build
.\build_exe.bat
```

### Find Your Files
```powershell
# Open Downloads folder
explorer %USERPROFILE%\Downloads

# View log file
notepad %USERPROFILE%\termoload.log

# View history
notepad %USERPROFILE%\.termoload_history.json
```

---

## 📝 Migration Notes

### For Existing Users
- Old downloads in `{app_dir}\downloads` will remain there
- New downloads use `C:\Users\{You}\Downloads`
- You can change this in Settings (press `s`)
- No data is lost during this update

### Settings Migration
- If `settings.json` exists, your preferences are kept
- Only the default path changes for new installs
- You can manually update the path in Settings tab

---

## 🔍 Troubleshooting

### Can't find log file?
```powershell
# Check if it exists
Test-Path "$env:USERPROFILE\termoload.log"

# If False, run the app once to create it
python app.py
```

### Downloads not going to right folder?
1. Press `s` in TermoLoad
2. Check "Download Folder" setting
3. Update if needed
4. Click "Save Settings"

### Want to use old download location?
```powershell
# Edit settings.json
notepad settings.json

# Change download_folder to:
{
  "download_folder": "E:\\TermoLoad\\downloads"
}
```

---

## Summary

✅ Cleaned up 8+ unnecessary files  
✅ Changed default downloads to Windows Downloads folder  
✅ Documented all file locations  
✅ Log file clearly documented at `%USERPROFILE%\termoload.log`  
✅ Created comprehensive file locations guide  
✅ Project structure now cleaner and more professional
