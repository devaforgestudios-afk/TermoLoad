# TermoLoad Testing Checklist - Torrent Fixes

## Build Info
- **Version**: October 20, 2025
- **Build Mode**: onedir console
- **Size**: 25.7 MB (TermoLoad.exe)
- **Location**: `dist\TermoLoad\`

## Major Fixes Included
✅ Comprehensive torrent crash fixes  
✅ Windows Firewall permission handling  
✅ Session initialization retries (5 attempts)  
✅ Better error handling and recovery  
✅ Temporary file cleanup  
✅ aiofiles lazy loading fix  
✅ Thread-safe file dialogs  

---

## 🔥 CRITICAL: Firewall Setup

### First Time Running
When you add your first torrent, Windows will show:

```
╔══════════════════════════════════════════════════════════╗
║  Windows Defender Firewall                               ║
║                                                           ║
║  Windows Defender Firewall has blocked some features     ║
║  of this app                                              ║
║                                                           ║
║  Name: TermoLoad.exe                                      ║
║  Publisher: Unknown Publisher                            ║
║                                                           ║
║  [✓] Private networks                                     ║
║  [✓] Public networks                                      ║
║                                                           ║
║          [ Allow access ]    [ Cancel ]                   ║
╚══════════════════════════════════════════════════════════╝
```

**YOU MUST CLICK "Allow access" for torrents to work!**

### Alternative: Manual Firewall Rule
If you don't see the prompt or accidentally clicked "Cancel":

1. Open Windows Defender Firewall with Advanced Security
2. Click "Inbound Rules" → "New Rule"
3. Select "Program" → Next
4. Browse to `E:\TermoLoad\dist\TermoLoad\TermoLoad.exe`
5. Select "Allow the connection"
6. Check all profiles (Domain, Private, Public)
7. Name it "TermoLoad"

---

## Testing Steps

### 1. Basic Functionality Test
```powershell
# Run the EXE
cd E:\TermoLoad\dist\TermoLoad
.\TermoLoad.exe
```

Expected: App starts within 2-5 seconds, no crashes

### 2. HTTP Download Test
1. Add a regular HTTP download
2. Verify it starts without issues
3. Check progress updates smoothly
4. Confirm download completes

### 3. Torrent Test - Magnet Link
1. Add a magnet link (e.g., from a legal torrent site)
2. **WATCH FOR FIREWALL POPUP** → Click "Allow access"
3. Wait for "Fetching Metadata" status
4. Should show countdown: "Metadata 60s" → "Metadata 59s" etc.
5. Once metadata received, download should start
6. Check peers/seeds count appears
7. Monitor progress updates every second

### 4. Torrent Test - .torrent File
1. Download a .torrent file to disk
2. Add it to TermoLoad (drag & drop or file picker)
3. Should start immediately (no metadata wait)
4. Verify download begins

### 5. Torrent Test - .torrent URL
1. Add a direct URL to a .torrent file
2. Should show "Downloading torrent..." status
3. Then start download after parsing

### 6. Error Recovery Test
Try these intentionally to verify graceful failure:
- Invalid magnet link → Should show "Error: Parse failed"
- Bad .torrent file → Should show "Error: Invalid torrent file"
- Timeout test (disconnect internet briefly) → Should show timeout error
- Cancel during metadata fetch → Should pause cleanly

---

## Log File Monitoring

### Location
```
C:\Users\<your-username>\termoload.log
```

### What to Look For

#### ✅ Good Signs
```
[TermoLoad] Torrent session started successfully
[TermoLoad] Please allow firewall access when prompted for torrent downloads
[TermoLoad] Firewall rule added for E:\TermoLoad\dist\TermoLoad\TermoLoad.exe
[RealDownloader] Torrent added successfully, handle valid: True
[TermoLoad] Metadata received after 5 seconds
[TermoLoad] T123: 25.5% | 1024.3KB/s | P:12 S:5 | Downloading
[TermoLoad] Torrent 123 completed!
```

#### ❌ Bad Signs (Report These)
```
NameError: name 'aiofiles' is not defined
AttributeError: 'NoneType' object has no attribute 'add_torrent'
RuntimeError: Invalid torrent handle
Segmentation fault
```

### Monitor in Real-Time
```powershell
# PowerShell - watch log updates
Get-Content $env:USERPROFILE\termoload.log -Tail 20 -Wait

# Filter for errors
Get-Content $env:USERPROFILE\termoload.log -Tail 50 | Select-String "error|Error|ERROR|exception"
```

---

## Performance Benchmarks

### Expected Startup Times
- **First run**: 3-5 seconds (loading all modules)
- **Subsequent runs**: 2-3 seconds (cached)
- **With many downloads**: May be slower due to state loading

### Expected Torrent Behavior
- **Magnet metadata fetch**: 2-60 seconds (depends on DHT)
- **Session initialization**: 0.5-2 seconds
- **Progress updates**: Every 1 second
- **Memory usage**: ~100-200 MB (normal for torrents)

---

## Common Issues & Solutions

### Issue: App crashes when adding torrent
**Check**: 
- Did you allow firewall access?
- Is port 6881 available (not used by another app)?
- Check log for specific error

**Solution**: 
- Allow firewall access
- Run as Administrator once
- Change port in code if needed

### Issue: "Error: Session failed"
**Check**: Log shows session creation errors

**Solution**: 
- Verify libtorrent is installed: `pip list | findstr libtorrent`
- Reinstall if needed: `pip install --force-reinstall python-libtorrent`

### Issue: "Error: Metadata timeout"
**Check**: Magnet link is valid, internet connected

**Solution**:
- Try a popular torrent (more seeds = faster metadata)
- Check firewall is allowing connections
- Wait longer (some magnets take time)

### Issue: Downloads stuck at 0%
**Check**: Peers/seeds count (shown in UI)

**Solution**:
- If 0 peers: Torrent may be dead, try another
- If peers exist but 0 speed: Firewall blocking, check settings
- Give it 1-2 minutes to find peers

### Issue: No firewall popup appeared
**Reason**: May happen if:
- Already allowed in previous version
- Antivirus is managing firewall
- Running in restricted environment

**Solution**: Add firewall rule manually (see above)

---

## What to Report

If you encounter crashes or errors, please provide:

1. **Steps to reproduce** (what you clicked, what torrent/link)
2. **Log excerpt** (last 50 lines before crash)
3. **Error message** (exact text from UI or log)
4. **System info** (Windows version, RAM, etc.)

### Get Last 50 Log Lines
```powershell
Get-Content $env:USERPROFILE\termoload.log -Tail 50 | Out-File desktop\termoload_error.txt
```

---

## Success Criteria

Your testing is successful if:
- ✅ App starts without crashes
- ✅ HTTP downloads work normally
- ✅ Firewall popup appears (or rule exists)
- ✅ Magnet links fetch metadata successfully
- ✅ .torrent files start downloading
- ✅ Progress updates smoothly every second
- ✅ Peers/seeds count is visible
- ✅ Downloads complete without crashes
- ✅ Log shows no critical errors

---

## Next Steps After Testing

### If Everything Works
1. You can distribute the entire `dist\TermoLoad\` folder
2. Recipients must allow firewall access on first run
3. Consider creating installer for easier distribution

### If Issues Found
1. Collect log file
2. Note exact steps to reproduce
3. Report back with details
4. We can add more error handling as needed

---

## Quick Command Reference

```powershell
# Run app
.\dist\TermoLoad\TermoLoad.exe

# View log
Get-Content $env:USERPROFILE\termoload.log -Tail 20

# Monitor log live
Get-Content $env:USERPROFILE\termoload.log -Tail 10 -Wait

# Search for errors
Select-String -Path $env:USERPROFILE\termoload.log -Pattern "error|crash|failed" -CaseSensitive:$false | Select-Object -Last 20

# Clear log (if it gets too big)
Clear-Content $env:USERPROFILE\termoload.log

# Check file size
(Get-Item $env:USERPROFILE\termoload.log).Length / 1MB
```

---

**Good luck with testing! 🚀**

Remember: The first torrent download will trigger the firewall popup - that's expected and required!
