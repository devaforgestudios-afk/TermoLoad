# TermoLoad Quick Reference

## 📍 Important File Locations

### Log File (3.5 MB currently)
```
C:\Users\adhdh\termoload.log
```
**Quick Open**: `notepad %USERPROFILE%\termoload.log`

### Download History
```
C:\Users\adhdh\.termoload_history.json
```

### Default Downloads Folder
```
C:\Users\adhdh\Downloads
```
**Quick Open**: `explorer %USERPROFILE%\Downloads`

### App Settings
```
E:\TermoLoad\settings.json
```

---

## 🚀 Quick Commands

### Run the App
```powershell
python app.py
```

### Build EXE (Fast Mode)
```powershell
.\build_fast.bat onedir console
```

### Run Built EXE
```powershell
dist\TermoLoad\TermoLoad.exe
```

### View Recent Logs
```powershell
Get-Content $env:USERPROFILE\termoload.log -Tail 50
```

### Open Downloads Folder
```powershell
explorer %USERPROFILE%\Downloads
```

---

## 📂 Project Files

| File | Purpose |
|------|---------|
| `app.py` | Main application (196 KB) |
| `FILE_LOCATIONS.md` | Complete file locations guide |
| `CLEANUP_SUMMARY.md` | Recent cleanup changes |
| `OPTIMIZATION_SUMMARY.md` | Performance optimizations |
| `BUILD_SUMMARY.md` | How to build the EXE |

---

## ⚙️ Recent Changes

✅ Cleaned up build artifacts and duplicate files  
✅ Default downloads now go to `C:\Users\{You}\Downloads`  
✅ All file locations documented  
✅ Faster EXE startup with lazy loading  
✅ Fixed torrent download crashes  
✅ Fixed EXE hanging on file dialogs  

---

## 🔍 Need Help?

- **Log file**: See `FILE_LOCATIONS.md`
- **Build issues**: See `BUILD_SUMMARY.md`
- **Performance**: See `OPTIMIZATION_SUMMARY.md`
- **Main docs**: See `README.md`
