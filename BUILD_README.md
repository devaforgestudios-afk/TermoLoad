# Building TermoLoad Executable

This guide explains how to build TermoLoad as a standalone Windows executable (.exe) file.

## Prerequisites

- Python 3.7 or higher installed
- All dependencies installed (see requirements.txt)

## Quick Build

Simply run the build script:

```batch
build_exe.bat
```

This script will:
1. Check if PyInstaller is installed (installs if needed)
2. Build the executable using the spec file
3. Create a standalone `TermoLoad.exe` in the `dist` folder

## Manual Build

If you prefer to build manually:

```batch
# Install PyInstaller
pip install pyinstaller

# Install dependencies
pip install -r requirements.txt

# Build the executable
pyinstaller build_exe.spec --clean
```

## Output

After successful build:
- **Executable location**: `dist\TermoLoad.exe`
- **Size**: Approximately 30-50 MB (includes all dependencies)
- **Type**: Single-file executable with bundled Python runtime

## Running the Executable

Simply double-click `dist\TermoLoad.exe` or run from command line:

```batch
dist\TermoLoad.exe
```

The executable is portable and can be copied to any Windows machine without requiring Python installation.

## Customization

### Adding an Icon

1. Create or obtain an `.ico` file
2. Edit `build_exe.spec` and change the icon line:
   ```python
   icon='path/to/your/icon.ico'
   ```
3. Rebuild with `build_exe.bat`

### Build Options

Edit `build_exe.spec` to customize:

- **Console mode**: `console=True` (shows terminal) or `console=False` (no terminal window)
- **UPX compression**: `upx=True` (smaller size) or `upx=False` (faster startup)
- **One-file vs one-folder**: Current spec creates one-file executable

## Troubleshooting

### Missing Dependencies

If the executable fails to run due to missing modules:

1. Add the module to `hiddenimports` in `build_exe.spec`:
   ```python
   hiddenimports=[
       'textual',
       'your_missing_module',
   ],
   ```
2. Rebuild with `build_exe.bat`

### Antivirus False Positives

Some antivirus software may flag PyInstaller executables. This is a known issue. You can:
- Add an exception in your antivirus
- Digitally sign the executable (requires code signing certificate)

### Large File Size

The executable includes the full Python runtime and all dependencies. To reduce size:
- Set `upx=True` in the spec file (if not already)
- Consider using one-folder mode instead (edit spec file)

## Distribution

The `TermoLoad.exe` file in the `dist` folder is completely standalone and can be:
- Copied to any Windows computer
- Shared with users who don't have Python installed
- Run directly without installation

## Notes

- First launch may be slower as Windows scans the new executable
- Download history is stored in `%USERPROFILE%\.termoload_history.json`
- Settings are stored in `settings.json` in the same folder as the executable
