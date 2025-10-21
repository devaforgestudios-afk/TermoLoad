# Core imports - keep these at top for fast startup
import os
import sys
import asyncio
import logging
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import deque

# Textual imports - needed for UI
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Button, Input, Label, Checkbox
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen

# ScrollView location changes between textual versions; try both locations
try:
    from textual.widgets import ScrollView  # type: ignore
except Exception:
    try:
        from textual.containers import ScrollView  # type: ignore
    except Exception:
        ScrollView = None

# Lazy imports - delay these until actually needed
# Will be imported when first used
_PIL_Image = None
_PIL_ImageDraw = None
_aiohttp = None
_aiofiles = None
_pystray = None
_tkinter = None
_tkinter_filedialog = None

def get_pil_modules():
    """Lazy load PIL modules."""
    global _PIL_Image, _PIL_ImageDraw
    if _PIL_Image is None:
        from PIL import Image, ImageDraw
        _PIL_Image = Image
        _PIL_ImageDraw = ImageDraw
    return _PIL_Image, _PIL_ImageDraw

def get_aiohttp():
    """Lazy load aiohttp."""
    global _aiohttp
    if _aiohttp is None:
        import aiohttp
        _aiohttp = aiohttp
    return _aiohttp

def get_aiofiles():
    """Lazy load aiofiles."""
    global _aiofiles
    if _aiofiles is None:
        import aiofiles
        _aiofiles = aiofiles
    return _aiofiles

def get_pystray():
    """Lazy load pystray."""
    global _pystray
    if _pystray is None:
        import pystray
        _pystray = pystray
    return _pystray

def get_tkinter():
    """Lazy load tkinter."""
    global _tkinter, _tkinter_filedialog
    if _tkinter is None:
        import tkinter as tk
        import tkinter.filedialog
        _tkinter = tk
        _tkinter_filedialog = tkinter.filedialog
    return _tkinter, _tkinter_filedialog

# Standard library imports
import random
import shutil
import subprocess
import ctypes

# Platform-specific imports
if sys.platform == 'win32':
    import winsound

from urllib.parse import urlparse
import queue
import concurrent.futures

def play_notification_sound(frequency=800, duration=150, sound_type='info'):
    """Cross-platform notification sound."""
    try:
        if sys.platform == 'win32':
            import winsound
            winsound.Beep(frequency, duration)
        elif sys.platform == 'darwin':
            # macOS uses afplay for system sounds
            sound_map = {
                'info': '/System/Library/Sounds/Glass.aiff',
                'complete': '/System/Library/Sounds/Hero.aiff',
                'error': '/System/Library/Sounds/Basso.aiff'
            }
            sound_file = sound_map.get(sound_type, sound_map['info'])
            subprocess.run(['afplay', sound_file], check=False, capture_output=True, timeout=2)
        elif sys.platform.startswith('linux'):
            # Linux - try multiple sound systems
            try:
                # Try paplay (PulseAudio) first
                subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], 
                             check=False, capture_output=True, timeout=2)
            except FileNotFoundError:
                try:
                    # Try aplay (ALSA) as fallback
                    subprocess.run(['aplay', '/usr/share/sounds/alsa/Front_Center.wav'],
                                 check=False, capture_output=True, timeout=2)
                except FileNotFoundError:
                    try:
                        # Try beep command as last resort
                        subprocess.run(['beep', '-f', str(frequency), '-l', str(duration)],
                                     check=False, capture_output=True, timeout=2)
                    except FileNotFoundError:
                        pass  # No sound available - silent operation
    except Exception as e:
        logging.debug(f"[TermoLoad] Could not play sound: {e}")

class TkinterDialogHelper:
    """Thread-safe async helper for tkinter file dialogs to prevent EXE hanging."""
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="TkDialog")
    
    @classmethod
    def _run_dialog_in_thread(cls, dialog_func):
        """Run a tkinter dialog in a separate thread to prevent blocking."""
        def wrapper():
            try:
                # Lazy load tkinter
                tk, tk_filedialog = get_tkinter()
                
                # Create a fresh root for each dialog to prevent state issues
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                root.update()
                
                # Run the dialog
                result = dialog_func(root, tk_filedialog)
                
                # Clean up
                try:
                    root.destroy()
                except:
                    pass
                
                return result
            except Exception as e:
                logging.exception(f"[TkinterHelper] Dialog error: {e}")
                return None
        
        # Run in thread pool to avoid blocking
        future = cls._executor.submit(wrapper)
        try:
            # Wait for result with timeout
            return future.result(timeout=300)  # 5 minute timeout
        except concurrent.futures.TimeoutError:
            logging.error("[TkinterHelper] Dialog timeout")
            return None
        except Exception as e:
            logging.exception(f"[TkinterHelper] Error running dialog: {e}")
            return None
    
    @classmethod
    def ask_open_filename(cls, title="Select File", filetypes=None):
        """Thread-safe file open dialog that won't hang in EXE."""
        def dialog_func(root, tk_filedialog):
            return tk_filedialog.askopenfilename(
                parent=root,
                title=title,
                filetypes=filetypes or [("All Files", "*.*")]
            )
        
        result = cls._run_dialog_in_thread(dialog_func)
        return result if result else None
    
    @classmethod
    def ask_directory(cls, title="Select Folder"):
        """Thread-safe directory selection dialog that won't hang in EXE."""
        def dialog_func(root, tk_filedialog):
            return tk_filedialog.askdirectory(
                parent=root,
                title=title
            )
        
        result = cls._run_dialog_in_thread(dialog_func)
        return result if result else None
    
    @classmethod
    def ask_save_filename(cls, title="Save As", filetypes=None, defaultextension=""):
        """Thread-safe save file dialog that won't hang in EXE."""
        def dialog_func(root, tk_filedialog):
            return tk_filedialog.asksaveasfilename(
                parent=root,
                title=title,
                filetypes=filetypes or [("All Files", "*.*")],
                defaultextension=defaultextension
            )
        
        result = cls._run_dialog_in_thread(dialog_func)
        return result if result else None
    
    @classmethod
    def cleanup(cls):
        """Clean up the thread pool."""
        try:
            cls._executor.shutdown(wait=False)
        except Exception:
            pass

class DownloadHistory:
    def __init__(self,app_instance):
        self.app = app_instance
        self.history_file = Path.home() / ".termoload_history.json"
        self.history = self.load_history()

    def load_history(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logging.exception("[TermoLoad] Failed to load download history")
            return []
    
    def save_history(self) -> None:
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            logging.exception("[TermoLoad] Failed to save download history")
    
    def add_entry(self,download: Dict[str, Any],completion_status:str):
        try:
            entry={
                "id":download.get("id"),
                "name":download.get("name"),
                "type":download.get("type"),
                "url" : download.get("url"),
                "size": download.get("total_size",0),
                "downloaded" : download.get("downloaded_bytes",0),
                "status": completion_status,
                "timestamp": time.time(),
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "filepath": download.get("filepath",""),
                "error": download.get("status") if completion_status=="failed" else None
            }
            self.history.append(entry)
            self.save_history()
        except Exception:
            logging.exception("[TermoLoad] Failed to add history entry")
    
    def get_statistics(self)-> Dict[str, Any]:
        try:
            total = len(self.history)
            completed = sum(1 for h in self.history if h.get("status") == "completed")
            failed = sum(1 for h in self.history if h.get("status") == "failed")
            cancelled = sum(1 for h in self.history if h.get("status") == "cancelled")

            total_size = sum(h.get("size", 0) for h in self.history if h.get("status") == "completed")
            total_downloaded = sum(h.get("downloaded", 0) for h in self.history)

            types={}
            for h in self.history:
                t = h.get("type","unknown")
                types[t] = types.get(t,0)+1
            week_ago = time.time() - (7*24*3600)
            recent = sum(1 for h in self.history if h.get("timestamp",0) > week_ago)
            success_rate = (completed / total * 100) if total > 0 else 0
            return{
                "total_downloads": total,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "success_rate": success_rate,
                "total_downloaded": total_downloaded,
                "by_type": types,
                "recent_week": recent
            }
        
        except Exception:
            logging.exception("[TermoLoad] Failed to compute statistics")
            return {}
    
    def clear_history(self):
            self.history = []
            self.save_history()
            logging.exception("[TermoLoad] Failed to clear history")
try:
    import libtorrent
    LIBTORRENT_AVAILABLE = True
except (ImportError, OSError) as e:
    libtorrent = None
    LIBTORRENT_AVAILABLE = False
    logging.warning(f"Libtorrent not available: {e}. Torrent downloads will be disabled.")

try:
    import yt_dlp as ytdlp
except Exception:
    ytdlp = None

# Set log file path to user's home directory
LOG_FILE_PATH = Path.home() / "termoload.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE_PATH), encoding='utf-8')
    ]
)

LOG_BUFFER = deque(maxlen=5000)


class BufferingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            LOG_BUFFER.append(msg)
        except Exception:
            pass

buffer_handler = BufferingHandler()
buffer_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(buffer_handler)

class RealDownloader:
    def __init__(self,app_instance):
        super().__init__()
        self.app = app_instance
        self.session = None
        self.torrent_session = None
        self.torrent_handles = {}

    def start_torrent_session(self):
        """Initialize libtorrent session with optimal settings and firewall handling"""
        if self.torrent_session is None and LIBTORRENT_AVAILABLE:
            try:
                import libtorrent as lt
                
                # Request firewall permission for Windows
                try:
                    self._request_firewall_permission()
                except Exception as fw_error:
                    logging.warning(f"[TermoLoad] Firewall permission request failed (non-critical): {fw_error}")
                
                # Create session with minimal but working settings
                # Using safer settings to avoid crashes
                settings = {
                    'listen_interfaces': '0.0.0.0:6881,[::]:6881',
                    'enable_outgoing_utp': True,
                    'enable_incoming_utp': True,
                    'enable_outgoing_tcp': True,
                    'enable_incoming_tcp': True,
                    'alert_mask': lt.alert.category_t.error_notification | 
                                  lt.alert.category_t.status_notification |
                                  lt.alert.category_t.storage_notification,
                }
                
                self.torrent_session = lt.session(settings)
                
                # Apply additional settings separately with error handling
                try:
                    sett = self.torrent_session.get_settings()
                    sett['user_agent'] = 'libtorrent/2.0'
                    sett['announce_to_all_tiers'] = True
                    sett['announce_to_all_trackers'] = True
                    sett['auto_manage_interval'] = 5
                    sett['connections_limit'] = 200
                    sett['download_rate_limit'] = 0
                    sett['upload_rate_limit'] = 0
                    self.torrent_session.apply_settings(sett)
                except Exception as settings_error:
                    logging.warning(f"[TermoLoad] Could not apply all settings: {settings_error}")
                
                # Add DHT bootstrap nodes with error handling
                try:
                    self.torrent_session.add_dht_router("router.bittorrent.com", 6881)
                    self.torrent_session.add_dht_router("router.utorrent.com", 6881)
                    self.torrent_session.add_dht_router("dht.transmissionbt.com", 6881)
                except Exception as dht_error:
                    logging.warning(f"[TermoLoad] DHT router setup failed (non-critical): {dht_error}")
                
                logging.info("[TermoLoad] Torrent session started successfully")
            except Exception as e:
                logging.exception(f"[TermoLoad] Failed to start torrent session: {e}")
                self.torrent_session = None
    
    def _request_firewall_permission(self):
        """Request firewall permission for torrent connections (cross-platform)"""
        try:
            import sys
            import subprocess
            import os
            
            # Handle different platforms
            if sys.platform == 'darwin':
                # macOS: System will prompt automatically for network access
                logging.info("[TermoLoad] macOS will prompt for network access if needed")
                return
            elif sys.platform.startswith('linux'):
                # Linux: Check if ufw is available and log helpful info
                try:
                    result = subprocess.run(['which', 'ufw'], 
                                          capture_output=True, timeout=1)
                    if result.returncode == 0:
                        logging.info("[TermoLoad] Linux firewall detected (ufw)")
                        logging.info("[TermoLoad] To allow torrents: sudo ufw allow 6881/tcp")
                        logging.info("[TermoLoad] To allow torrents: sudo ufw allow 6881/udp")
                except:
                    pass
                return
            elif sys.platform != 'win32':
                # Other platforms
                return
            
            # Windows-specific code continues below
            # Get the executable path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_path = sys.executable
            else:
                # Running as script
                exe_path = sys.executable
            
            # Check if running with admin rights (Windows only at this point)
            try:
                is_admin = os.getuid() == 0
            except AttributeError:
                # Windows
                if sys.platform == 'win32':
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                else:
                    is_admin = False
            
            if is_admin:
                # Add firewall rule using netsh
                app_name = "TermoLoad"
                try:
                    # Remove existing rule if any
                    subprocess.run(
                        ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={app_name}'],
                        capture_output=True,
                        timeout=5
                    )
                except:
                    pass
                
                # Add new rule
                subprocess.run(
                    ['netsh', 'advfirewall', 'firewall', 'add', 'rule', 
                     f'name={app_name}', 
                     'dir=in', 
                     'action=allow', 
                     f'program={exe_path}',
                     'enable=yes'],
                    capture_output=True,
                    timeout=5,
                    check=False
                )
                logging.info(f"[TermoLoad] Firewall rule added for {exe_path}")
            else:
                # Show notification to user to allow firewall access
                logging.info("[TermoLoad] Please allow firewall access when prompted for torrent downloads")
                # Windows will automatically prompt when port binding occurs
                
        except Exception as e:
            logging.warning(f"[TermoLoad] Firewall setup warning: {e}")
    
    async def get_torrent_info(self, url: str, download_id: int) -> Optional[dict]:
        """Fetch torrent metadata without starting download."""
        temp_file = None
        try:
            # Lazy load aiofiles when needed
            aiofiles = get_aiofiles()
            
            if not LIBTORRENT_AVAILABLE:
                logging.warning("[TermoLoad] Libtorrent not available for torrent info")
                return None
            
            if self.torrent_session is None:
                logging.info("[TermoLoad] Starting torrent session for info fetch...")
                self.start_torrent_session()
                await asyncio.sleep(0.5)  # Give session time to initialize
            
            if self.torrent_session is None:
                logging.error("[TermoLoad] Failed to create torrent session")
                return None
            
            import libtorrent as lt
            
            # Prepare parameters
            params = lt.add_torrent_params()
            params.save_path = str(Path("temp_info"))
            
            # Parse based on type with comprehensive error handling
            try:
                if url.startswith("magnet:"):
                    logging.info("[TermoLoad] Parsing magnet link for info...")
                    params = lt.parse_magnet_uri(url)
                    params.save_path = str(Path("temp_info"))
                    params.flags |= lt.torrent_flags.upload_mode  # Don't download, just get metadata
                    
                elif os.path.isfile(url):
                    logging.info(f"[TermoLoad] Reading torrent file for info: {url}")
                    try:
                        info = lt.torrent_info(url)
                        params.ti = info
                    except Exception as file_error:
                        logging.error(f"[TermoLoad] Failed to read torrent file: {file_error}")
                        return None
                    
                elif url.startswith(("http://", "https://")) and url.endswith(".torrent"):
                    logging.info("[TermoLoad] Downloading torrent file for info...")
                    await self.start_session()
                    
                    try:
                        async with self.session.get(url, timeout=30) as response:
                            if response.status == 200:
                                torrent_data = await response.read()
                                temp_file = Path("temp_info") / f"temp_{download_id}.torrent"
                                temp_file.parent.mkdir(parents=True, exist_ok=True)
                                
                                async with aiofiles.open(temp_file, "wb") as f:
                                    await f.write(torrent_data)
                                
                                info = lt.torrent_info(str(temp_file))
                                params.ti = info
                            else:
                                logging.error(f"[TermoLoad] HTTP error downloading torrent: {response.status}")
                                return None
                    except asyncio.TimeoutError:
                        logging.error("[TermoLoad] Timeout downloading torrent file")
                        return None
                    except Exception as download_error:
                        logging.exception(f"[TermoLoad] Error downloading torrent: {download_error}")
                        return None
                else:
                    logging.error(f"[TermoLoad] Invalid torrent source: {url}")
                    return None
            
            except Exception as parse_error:
                logging.exception(f"[TermoLoad] Failed to parse torrent source: {parse_error}")
                return None
            
            # Add torrent temporarily to get info with error handling
            try:
                handle = self.torrent_session.add_torrent(params)
                
                if not handle.is_valid():
                    logging.error("[TermoLoad] Invalid handle returned")
                    return None
                    
            except Exception as add_error:
                logging.exception(f"[TermoLoad] Failed to add torrent for info: {add_error}")
                return None
            
            # Wait for metadata if magnet with timeout
            if url.startswith("magnet:"):
                logging.info("[TermoLoad] Waiting for magnet metadata...")
                metadata_received = False
                
                for i in range(60):
                    try:
                        if not handle.is_valid():
                            logging.warning("[TermoLoad] Handle became invalid")
                            break
                            
                        status = handle.status()
                        if status.has_metadata:
                            logging.info(f"[TermoLoad] Metadata received after {i+1}s")
                            metadata_received = True
                            break
                            
                        await asyncio.sleep(1)
                    except Exception as status_error:
                        logging.warning(f"[TermoLoad] Error checking metadata: {status_error}")
                        await asyncio.sleep(1)
                        continue
                
                if not metadata_received:
                    logging.error("[TermoLoad] Metadata timeout")
                    try:
                        self.torrent_session.remove_torrent(handle)
                    except:
                        pass
                    return None
            
            # Extract file information with error handling
            try:
                status = handle.status()
                torrent_info_obj = handle.torrent_file()
                
                files_info = []
                if torrent_info_obj:
                    for i in range(torrent_info_obj.num_files()):
                        try:
                            file_entry = torrent_info_obj.files().at(i)
                            files_info.append({
                                "index": i,
                                "path": file_entry.path,
                                "size": file_entry.size
                            })
                        except Exception as file_error:
                            logging.warning(f"[TermoLoad] Error reading file {i}: {file_error}")
                            continue
                
                result = {
                    "name": status.name if status.has_metadata else "Unknown",
                    "total_size": status.total_wanted,
                    "num_files": len(files_info),
                    "files": files_info,
                    "handle": handle  # Keep handle for later use
                }
                
                # Don't remove handle yet - we'll use it for actual download
                # Store temporarily
                self.torrent_handles[f"temp_{download_id}"] = handle
                
                logging.info(f"[TermoLoad] Torrent info retrieved: {result['name']}, {len(files_info)} files")
                return result
                
            except Exception as extract_error:
                logging.exception(f"[TermoLoad] Failed to extract torrent info: {extract_error}")
                try:
                    self.torrent_session.remove_torrent(handle)
                except:
                    pass
                return None
                
        except Exception as e:
            logging.exception(f"[TermoLoad] Failed to get torrent info: {e}")
            return None
        
        finally:
            # Cleanup temporary file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logging.info("[TermoLoad] Cleaned up temp torrent file")
                except Exception as cleanup_error:
                    logging.warning(f"[TermoLoad] Could not cleanup temp file: {cleanup_error}")

    async def download_torrent(self, url: str, download_id: int, custom_path: str, selected_files: Optional[List[int]] = None) -> bool:
        """Download torrent from magnet link, .torrent file, or URL with optional file selection."""
        torrent_data_file = None
        try:
            # Lazy load aiofiles when needed
            aiofiles = get_aiofiles()
            
            if not LIBTORRENT_AVAILABLE:
                self.update_download_progress(
                    download_id, 0.0, 0, 0, "Error: Libtorrent not available"
                )
                logging.error("[RealDownloader] Libtorrent unavailable")
                return False
            
            # Check if we have a temporary handle from info fetch
            temp_key = f"temp_{download_id}"
            handle = self.torrent_handles.pop(temp_key, None)
            
            if handle is None:
                # Initialize session if needed with retries
                if self.torrent_session is None:
                    logging.info("[RealDownloader] Starting torrent session...")
                    self.update_download_progress(download_id, 0.0, 0, 0, "Initializing...")
                    await asyncio.sleep(0.2)  # Give UI time to update
                    
                    # Try to start session
                    self.start_torrent_session()
                    
                    # Wait and verify session started
                    for retry in range(5):
                        await asyncio.sleep(0.5)
                        if self.torrent_session is not None:
                            break
                        logging.warning(f"[RealDownloader] Session not ready, retry {retry+1}/5")
                    
                    if self.torrent_session is None:
                        self.update_download_progress(
                            download_id, 0.0, 0, 0, "Error: Session failed"
                        )
                        logging.error("[RealDownloader] Torrent session creation failed after retries")
                        return False
                
                save_path = Path(custom_path or "downloads")
                save_path.mkdir(parents=True, exist_ok=True)
                
                # Prepare torrent parameters with error handling
                import libtorrent as lt
                params = lt.add_torrent_params()
                params.save_path = str(save_path)
                
                # Add torrent based on type with comprehensive error handling
                try:
                    if url.startswith("magnet:"):
                        logging.info(f"[TermoLoad] Adding magnet link")
                        self.update_download_progress(download_id, 0.0, 0, 0, "Parsing magnet...")
                        params = lt.parse_magnet_uri(url)
                        params.save_path = str(save_path)
                        
                    elif os.path.isfile(url):
                        logging.info(f"[TermoLoad] Adding torrent file: {url}")
                        self.update_download_progress(download_id, 0.0, 0, 0, "Reading file...")
                        
                        # Read torrent file with better error handling
                        try:
                            info = lt.torrent_info(url)
                            params.ti = info
                        except Exception as file_error:
                            logging.error(f"[TermoLoad] Failed to read torrent file: {file_error}")
                            self.update_download_progress(
                                download_id, 0.0, 0, 0, f"Error: Invalid torrent file"
                            )
                            return False
                        
                    elif url.startswith(("http://", "https://")) and url.endswith(".torrent"):
                        logging.info(f"[TermoLoad] Downloading .torrent from URL")
                        self.update_download_progress(download_id, 0.0, 0, 0, "Downloading torrent...")
                        
                        await self.start_session()
                        
                        try:
                            async with self.session.get(url, timeout=30) as response:
                                if response.status == 200:
                                    torrent_data = await response.read()
                                    torrent_data_file = save_path / f"temp_{download_id}.torrent"
                                    
                                    async with aiofiles.open(torrent_data_file, "wb") as f:
                                        await f.write(torrent_data)
                                    
                                    info = lt.torrent_info(str(torrent_data_file))
                                    params.ti = info
                                else:
                                    self.update_download_progress(
                                        download_id, 0.0, 0, 0, f"Error: HTTP {response.status}"
                                    )
                                    logging.error(f"[TermoLoad] Failed to download torrent: HTTP {response.status}")
                                    return False
                        except asyncio.TimeoutError:
                            self.update_download_progress(
                                download_id, 0.0, 0, 0, "Error: Download timeout"
                            )
                            logging.error("[TermoLoad] Torrent download timeout")
                            return False
                        except Exception as download_error:
                            self.update_download_progress(
                                download_id, 0.0, 0, 0, f"Error: {str(download_error)[:30]}"
                            )
                            logging.exception(f"[TermoLoad] Torrent download failed: {download_error}")
                            return False
                    else:
                        self.update_download_progress(
                            download_id, 0.0, 0, 0, "Error: Invalid source"
                        )
                        logging.error(f"[TermoLoad] Invalid torrent source: {url}")
                        return False
                    
                except Exception as parse_error:
                    logging.exception(f"[RealDownloader] Failed to parse torrent: {parse_error}")
                    self.update_download_progress(
                        download_id, 0.0, 0, 0, f"Error: Parse failed"
                    )
                    return False
                
                # Add torrent to session with comprehensive error handling
                try:
                    logging.info(f"[RealDownloader] Adding torrent to session...")
                    self.update_download_progress(download_id, 0.0, 0, 0, "Adding to session...")
                    
                    # Verify session is still valid
                    if self.torrent_session is None:
                        raise RuntimeError("Torrent session became None")
                    
                    handle = self.torrent_session.add_torrent(params)
                    
                    # Verify handle is valid
                    if not handle.is_valid():
                        raise RuntimeError("Invalid torrent handle returned")
                    
                    logging.info(f"[RealDownloader] Torrent added successfully, handle valid: {handle.is_valid()}")
                    
                except Exception as add_error:
                    logging.exception(f"[RealDownloader] Failed to add torrent to session: {add_error}")
                    self.update_download_progress(
                        download_id, 0.0, 0, 0, f"Error: Cannot add torrent"
                    )
                    return False
                
                # Wait for metadata if magnet with timeout and better error handling
                if url.startswith("magnet:"):
                    self.update_download_progress(download_id, 0.0, 0, 0, "Fetching Metadata")
                    logging.info(f"[TermoLoad] Waiting for metadata...")
                    
                    metadata_received = False
                    for i in range(60):
                        try:
                            if not handle.is_valid():
                                logging.error("[TermoLoad] Handle became invalid while waiting for metadata")
                                break
                                
                            status = handle.status()
                            if status.has_metadata:
                                logging.info(f"[TermoLoad] Metadata received after {i+1} seconds")
                                metadata_received = True
                                break
                                
                            # Update progress with countdown
                            self.update_download_progress(
                                download_id, 0.0, 0, 0, f"Metadata {60-i}s"
                            )
                            await asyncio.sleep(1)
                        except Exception as status_error:
                            logging.warning(f"[TermoLoad] Error checking metadata status: {status_error}")
                            await asyncio.sleep(1)
                            continue
                    
                    if not metadata_received:
                        self.update_download_progress(
                            download_id, 0.0, 0, 0, "Error: Metadata timeout"
                        )
                        logging.error("[TermoLoad] Metadata fetch timeout")
                        try:
                            self.torrent_session.remove_torrent(handle)
                        except:
                            pass
                        return False
            else:
                # Use existing handle from get_torrent_info
                save_path = Path(custom_path or "downloads")
                save_path.mkdir(parents=True, exist_ok=True)
                # Move handle to correct save path
                try:
                    handle.move_storage(str(save_path))
                except:
                    pass
                # Clear upload_mode flag if it was set
                try:
                    import libtorrent as lt
                    handle.unset_flags(lt.torrent_flags.upload_mode)
                except:
                    pass
            
            # Apply file selection if specified
            if selected_files is not None:
                try:
                    torrent_info_obj = handle.torrent_file()
                    if torrent_info_obj:
                        num_files = torrent_info_obj.num_files()
                        # Set priority to 0 (don't download) for unselected files
                        for i in range(num_files):
                            if i in selected_files:
                                handle.file_priority(i, 4)  # Normal priority
                            else:
                                handle.file_priority(i, 0)  # Don't download
                        logging.info(f"[TermoLoad] Set file priorities: {len(selected_files)}/{num_files} files selected")
                except Exception as e:
                    logging.warning(f"[TermoLoad] Failed to set file priorities: {e}")
            
            # Store handle
            self.torrent_handles[download_id] = handle
            
            logging.info(f"[TermoLoad] Torrent added to session: {download_id}")
            
            # Update torrent name
            try:
                status = handle.status()
                if status.has_metadata:
                    torrent_name = status.name
                    for d in self.app.downloads:
                        if d.get("id") == download_id:
                            d["name"] = torrent_name
                            # Add file selection info
                            if selected_files is not None:
                                torrent_info_obj = handle.torrent_file()
                                d["selected_files"] = len(selected_files)
                                d["total_files"] = torrent_info_obj.num_files() if torrent_info_obj else 0
                            break
                    logging.info(f"[TermoLoad] Torrent name: {torrent_name}")
            except Exception as e:
                logging.warning(f"[TermoLoad] Could not get torrent name: {e}")
            
            # Resume download
            try:
                handle.resume()
            except:
                pass
            
            # Main download loop
            logging.info(f"[TermoLoad] Starting download loop for torrent {download_id}")
            iteration = 0
            
            while download_id in self.torrent_handles:
                try:
                    if not handle.is_valid():
                        logging.warning(f"[TermoLoad] Handle became invalid")
                        break
                    
                    status = handle.status()
                    iteration += 1
                    
                    # Get status info
                    state = status.state
                    progress = status.progress
                    download_rate = status.download_rate
                    total_size = status.total_wanted
                    downloaded = status.total_wanted_done
                    num_peers = status.num_peers
                    num_seeds = status.num_seeds
                    
                    # Calculate ETA
                    if download_rate > 0 and total_size > 0:
                        remaining = total_size - downloaded
                        eta_seconds = remaining / download_rate
                    else:
                        eta_seconds = 0
                    
                    # Update peer/seed count
                    self.update_torrent_peers(download_id, num_peers, num_seeds)
                    
                    # Update size info
                    try:
                        for d in self.app.downloads:
                            if d.get("id") == download_id:
                                d["total_size"] = total_size
                                d["downloaded_bytes"] = downloaded
                                break
                    except:
                        pass
                    
                    # Determine status text
                    state_str = str(status.state)
                    if "checking" in state_str.lower():
                        status_text = "Checking Files"
                    elif "downloading_metadata" in state_str.lower():
                        status_text = "Fetching Metadata"
                    elif "downloading" in state_str.lower():
                        status_text = "Downloading"
                    elif "finished" in state_str.lower() or state == 5:
                        status_text = "Completed"
                    elif "seeding" in state_str.lower() or state == 6:
                        status_text = "Seeding"
                    elif num_peers == 0 and download_rate == 0:
                        status_text = "Finding Peers"
                    else:
                        status_text = "Downloading"
                    
                    # Update progress
                    self.update_download_progress(
                        download_id,
                        progress,
                        download_rate,
                        eta_seconds,
                        status_text
                    )
                    
                    # Log every 10 seconds
                    if iteration % 10 == 1:
                        logging.info(
                            f"[TermoLoad] T{download_id}: {progress*100:.1f}% "
                            f"| {download_rate/1024:.1f}KB/s | "
                            f"P:{num_peers} S:{num_seeds} | {status_text}"
                        )
                    
                    # Check if complete
                    if status.is_finished or progress >= 0.999:
                        logging.info(f"[TermoLoad] Torrent {download_id} completed!")
                        
                        # Save file path
                        try:
                            for d in self.app.downloads:
                                if d.get("id") == download_id:
                                    d["filepath"] = str(save_path / status.name)
                                    break
                        except:
                            pass
                        
                        self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                        
                        try:
                            self.app.save_downloads_state(force=True)
                        except:
                            pass
                        
                        self.torrent_handles.pop(download_id, None)
                        return True
                    
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    logging.exception(f"[TermoLoad] Error in download loop: {e}")
                    await asyncio.sleep(1.0)
            
            return False
            
        except asyncio.CancelledError:
            logging.info(f"[TermoLoad] Torrent {download_id} cancelled")
            try:
                handle = self.torrent_handles.get(download_id)
                if handle and handle.is_valid():
                    handle.pause()
                for d in self.app.downloads:
                    if d.get("id") == download_id:
                        d["status"] = "Paused"
                        break
                self.app.save_downloads_state(force=True)
            except:
                pass
            return False
            
        except Exception as e:
            logging.exception(f"[TermoLoad] Torrent download error: {e}")
            self.update_download_progress(
                download_id, 0, 0, 0, f"Error: {str(e)[:50]}"
            )
            try:
                self.app.save_downloads_state(force=True)
            except:
                pass
            return False
        
        finally:
            # Cleanup temporary torrent file
            if torrent_data_file and torrent_data_file.exists():
                try:
                    torrent_data_file.unlink()
                    logging.info(f"[TermoLoad] Cleaned up temporary torrent file")
                except Exception as cleanup_error:
                    logging.warning(f"[TermoLoad] Could not cleanup temp file: {cleanup_error}")
    
    def stop_torrent(self,download_id:int):
        try:
            handle = self.torrent_handles.get(download_id)
            if handle:
                handle.pause()
                logging.info(f"[TermoLoad] Torrent paused: {download_id}")
        except Exception:
            logging.exception(f"[TermoLoad] Failed to pause torrent {download_id}")

    def pause_torrent(self,download_id:int):
        self.stop_torrent(download_id)

    def remove_torrent(self,download_id:int):
        try:
            handle = self.torrent_handles.pop(download_id, None)
            if handle and self.torrent_session:
                self.torrent_session.remove_torrent(handle)
                logging.info(f"[TermoLoad] Torrent removed: {download_id}")
        except Exception:
            logging.exception(f"[TermoLoad] Failed to remove torrent {download_id}")


    async def start_session(self):
        if not self.session:
            # Lazy load aiohttp
            aiohttp = get_aiohttp()
            
            try:
                connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
            except Exception:
                connector = None
            default_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36 TermoLoad/1.0",
                "Accept": "*/*",
            }
            self.session = (
                aiohttp.ClientSession(connector=connector, headers=default_headers)
                if connector
                else aiohttp.ClientSession(headers=default_headers)
            )

    

    async def download_with_ytdlp(self,url:str,download_id:int, custom_path: str, filename:str | None = None, audio_only:bool = False, ytdlp_format:str | None = None)->bool:
        if ytdlp is None:
            self.update_download_progress(download_id, 0.0, 0, 0, "Error: yt-dlp not installed")
            logging.error("[TermoLoad] yt-dlp not installed, cannot download video URLs")
            return False
        try:
            Path(custom_path or "downloads").mkdir(parents=True, exist_ok=True)
            if filename:
                outtmpl = str((Path(custom_path)/filename).with_suffix(".%(ext)s"))
            else:
                outtmpl = str(Path(custom_path)/"%(title)s.%(ext)s")
            
            def _hook(d: dict):
                status = d.get("status")
                if status == "downloading":
                    downloaded = int(d.get("downloaded_bytes") or 0)
                    total = int(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
                    speed = float(d.get("speed") or 0)
                    eta = float(d.get("eta") or 0)
                    progress = (downloaded / total) if total else 0.0
                    try:
                        item = next((x for x in self.app.downloads if x.get("id") == download_id), None)
                        if item is not None:
                            item["downloaded_bytes"] = downloaded
                            if total:
                                item["total_size"] = total
                    except Exception:
                        pass
                    self.update_download_progress(download_id, progress, speed, eta, "Downloading")

                elif status == "finished":
                    self.update_download_progress(download_id,1.0,0,0, "Processing")
                        
            ytdlp_opts = {
                "outtmpl": outtmpl,
                "noprogress": True,
                "progress_hooks": [_hook],
                "continuedl": True,
                "retries" : 5,
                "ignoreerrors": True,
                "concurrent_fragment_downloads": 5,
            }
            if audio_only:
                ytdlp_opts["format"] = "bestaudio/best"
                ytdlp_opts["postprocessors"] = [
                    {"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}
                    ]
            else:
                ytdlp_opts["format"] = ytdlp_format or "bestvideo+bestaudio/best"
                ytdlp_opts["merge_output_format"] = "mp4"
            
            def _run():
                with ytdlp.YoutubeDL(ytdlp_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    try:
                        final_path = info.get("requested_downloads", [{}])[0].get("filepath") or info.get("filepath")
                        if final_path:
                            for item in self.app.downloads:
                                if item.get("id") == download_id:
                                    item["filepath"] = final_path
                                    try:
                                        item["name"] = os.path.basename(final_path)
                                    except Exception:
                                        pass
                                    break
                    except Exception:
                        pass
            
            await asyncio.to_thread(_run)
            self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
            try:
                self.app.save_downloads_state(force=True)
            except Exception:
                pass
            return True
        except asyncio.CancelledError:
            try:
                d = next((x for x in self.app.downloads if x.get("id") == download_id),None)
                if d:
                    total = int(d.get("total_size") or 0)
                    done = int(d.get("downloaded_bytes") or 0)
                    progress = (done / total) if total else d.get("progress", 0.0)
                    self.update_download_progress(download_id, progress, 0, 0, "Paused")
                    self.app.save_downloads_state(force=True)
            except Exception:
                pass
            return False
        except Exception as e:
            logging.exception(f"[TermoLoad] download_with_ytdlp exception id={download_id}: {e}")
            self.update_download_progress(download_id, 0, 0, 0, f"Error:{str(e)}")
            try:
                self.app.save_downloads_state(force=True)
            except Exception:
                pass
            return False
   
    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def download_file(self,url:str,download_id:int,filename:str = None, custom_path: str = "downloads"):
        try:
            # Lazy load aiofiles when needed
            aiofiles = get_aiofiles()
            
            logging.info(f"[TermoLoad] Starting download_file id={download_id} url={url} path={custom_path}")
            await self.start_session()

            if not filename:
                parsed = urlparse(url)
                filename = os.path.basename(parsed.path) or f"download_{download_id}"

            download_dir = Path(custom_path or "downloads")
            download_dir.mkdir(parents=True, exist_ok=True)
            filepath = download_dir / filename

            # Determine if we can resume
            existing_size = 0
            if filepath.exists():
                try:
                    existing_size = filepath.stat().st_size
                except Exception:
                    existing_size = 0

            headers = {}
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"

            async with self.session.get(url, headers=headers) as response:
                status = response.status
                if status == 206:
                    part_len = int(response.headers.get("content-length", 0))
                    total_size = None
                    cr = response.headers.get("content-range") or response.headers.get("Content-Range")
                    if cr:
                        try:
                            after_slash = cr.split("/")[-1]
                            if after_slash.strip().isdigit():
                                total_size = int(after_slash.strip())
                        except Exception:
                            total_size = None
                    if total_size is None and part_len > 0:
                        total_size = existing_size + part_len
                    open_mode = 'ab'
                    downloaded = existing_size
                elif status == 200:
                    total_size = int(response.headers.get('content-length', 0)) or None
                    open_mode = 'wb'
                    downloaded = 0
                    if existing_size > 0:
                        try:
                            filepath.unlink(missing_ok=True)
                        except Exception:
                            pass
                elif status == 416:
                    try:
                        cr = response.headers.get("content-range") or response.headers.get("Content-Range")
                        total_len = None
                        if cr and "/" in cr:
                            length_part = cr.split("/")[-1].strip()
                            if length_part.isdigit():
                                total_len = int(length_part)
                    except Exception:
                        total_len = None

                    if total_len is not None and existing_size == total_len and total_len > 0:
                        try:
                            for d in self.app.downloads:
                                if d.get("id") == download_id:
                                    d["filepath"] = str(filepath)
                                    d["total_size"] = total_len
                                    d["downloaded_bytes"] = total_len
                                    break
                        except Exception:
                            pass
                        self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                        try:
                            self.app.save_downloads_state(force=True)
                        except Exception:
                            pass
                        return True

                    try:
                        if filepath.exists():
                            filepath.unlink(missing_ok=True)
                    except Exception:
                        pass
                    async with self.session.get(url, headers={"Range": "bytes=0-"}) as r2:
                        if r2.status == 200:
                            total_size = int(r2.headers.get('content-length', 0)) or None
                            open_mode = 'wb'
                            downloaded = 0
                            try:
                                for d in self.app.downloads:
                                    if d.get("id") == download_id:
                                        d["filepath"] = str(filepath)
                                        d["total_size"] = total_size if total_size is not None else 0
                                        d["downloaded_bytes"] = downloaded
                                        d["status"] = "Downloading"
                                        break
                            except Exception:
                                pass

                            start_time = time.time()
                            chunk_size = 256 * 1024
                            ema_speed = None
                            ema_alpha = 0.2
                            last_t = start_time
                            bytes_window = 0
                            async with aiofiles.open(filepath, open_mode) as file:
                                idx = 0
                                async for chunk in r2.content.iter_chunked(chunk_size):
                                    if not chunk:
                                        await asyncio.sleep(0)
                                        continue
                                    await file.write(chunk)
                                    downloaded += len(chunk)
                                    bytes_window += len(chunk)

                                    progress = (downloaded / total_size) if (total_size and total_size > 0) else 0
                                    now = time.time()
                                    dt = now - last_t
                                    inst_speed = (bytes_window / dt) if dt > 0 else 0
                                    bytes_window = 0
                                    last_t = now
                                    if ema_speed is None:
                                        ema_speed = inst_speed
                                    else:
                                        ema_speed = ema_alpha * inst_speed + (1 - ema_alpha) * ema_speed
                                    speed = ema_speed or 0
                                    eta = ((total_size - downloaded) / speed) if (total_size and speed > 0) else 0
                                    try:
                                        for d in self.app.downloads:
                                            if d.get("id") == download_id:
                                                d["downloaded_bytes"] = downloaded
                                                if total_size:
                                                    d["total_size"] = total_size
                                                d["_smoothed_bps"] = speed
                                                break
                                    except Exception:
                                        pass

                                    self.update_download_progress(download_id, progress, speed, eta, "Downloading")
                                    idx += 1
                                    if (idx % 8) == 0:
                                        await asyncio.sleep(0)

                            if total_size and downloaded >= total_size:
                                self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                            else:
                                self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                            try:
                                self.app.save_downloads_state(force=True)
                            except Exception:
                                pass
                            return True
                        elif r2.status == 206:
                            total_size = int(r2.headers.get('content-length', 0)) or None
                            open_mode = 'wb'
                            downloaded = 0
                            try:
                                for d in self.app.downloads:
                                    if d.get("id") == download_id:
                                        d["filepath"] = str(filepath)
                                        d["total_size"] = total_size if total_size is not None else 0
                                        d["downloaded_bytes"] = downloaded
                                        d["status"] = "Downloading"
                                        break
                            except Exception:
                                pass
                            start_time = time.time()
                            chunk_size = 256 * 1024
                            ema_speed = None
                            ema_alpha = 0.2
                            last_t = start_time
                            bytes_window = 0
                            async with aiofiles.open(filepath, open_mode) as file:
                                idx = 0
                                async for chunk in r2.content.iter_chunked(chunk_size):
                                    if not chunk:
                                        await asyncio.sleep(0)
                                        continue
                                    await file.write(chunk)
                                    downloaded += len(chunk)
                                    bytes_window += len(chunk)
                                    progress = (downloaded / total_size) if (total_size and total_size > 0) else 0
                                    now = time.time()
                                    dt = now - last_t
                                    inst_speed = (bytes_window / dt) if dt > 0 else 0
                                    bytes_window = 0
                                    last_t = now
                                    if ema_speed is None:
                                        ema_speed = inst_speed
                                    else:
                                        ema_speed = ema_alpha * inst_speed + (1 - ema_alpha) * ema_speed
                                    speed = ema_speed or 0
                                    eta = ((total_size - downloaded) / speed) if (total_size and speed > 0) else 0
                                    try:
                                        for d in self.app.downloads:
                                            if d.get("id") == download_id:
                                                d["downloaded_bytes"] = downloaded
                                                if total_size:
                                                    d["total_size"] = total_size
                                                d["_smoothed_bps"] = speed
                                                break
                                    except Exception:
                                        pass
                                    self.update_download_progress(download_id, progress, speed, eta, "Downloading")
                                    idx += 1
                                    if (idx % 8) == 0:
                                        await asyncio.sleep(0)
                            if total_size and downloaded >= total_size:
                                self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                            else:
                                self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                            try:
                                self.app.save_downloads_state(force=True)
                            except Exception:
                                pass
                            return True
                        else:
                            # Final fallback: plain GET without Range
                            async with self.session.get(url) as r3:
                                if r3.status == 200:
                                    total_size = int(r3.headers.get('content-length', 0)) or None
                                    open_mode = 'wb'
                                    downloaded = 0
                                    try:
                                        for d in self.app.downloads:
                                            if d.get("id") == download_id:
                                                d["filepath"] = str(filepath)
                                                d["total_size"] = total_size if total_size is not None else 0
                                                d["downloaded_bytes"] = downloaded
                                                d["status"] = "Downloading"
                                                break
                                    except Exception:
                                        pass
                                    start_time = time.time()
                                    chunk_size = 256 * 1024
                                    ema_speed = None
                                    ema_alpha = 0.2
                                    last_t = start_time
                                    bytes_window = 0
                                    async with aiofiles.open(filepath, open_mode) as file:
                                        idx = 0
                                        async for chunk in r3.content.iter_chunked(chunk_size):
                                            if not chunk:
                                                await asyncio.sleep(0)
                                                continue
                                            await file.write(chunk)
                                            downloaded += len(chunk)
                                            bytes_window += len(chunk)
                                            progress = (downloaded / total_size) if (total_size and total_size > 0) else 0
                                            now = time.time()
                                            dt = now - last_t
                                            inst_speed = (bytes_window / dt) if dt > 0 else 0
                                            bytes_window = 0
                                            last_t = now
                                            if ema_speed is None:
                                                ema_speed = inst_speed
                                            else:
                                                ema_speed = ema_alpha * inst_speed + (1 - ema_alpha) * ema_speed
                                            speed = ema_speed or 0
                                            eta = ((total_size - downloaded) / speed) if (total_size and speed > 0) else 0
                                            try:
                                                for d in self.app.downloads:
                                                    if d.get("id") == download_id:
                                                        d["downloaded_bytes"] = downloaded
                                                        if total_size:
                                                            d["total_size"] = total_size
                                                        d["_smoothed_bps"] = speed
                                                        break
                                            except Exception:
                                                pass
                                            self.update_download_progress(download_id, progress, speed, eta, "Downloading")
                                            idx += 1
                                            if (idx % 8) == 0:
                                                await asyncio.sleep(0)
                                    if total_size and downloaded >= total_size:
                                        self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                                    else:
                                        self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                                    try:
                                        self.app.save_downloads_state(force=True)
                                    except Exception:
                                        pass
                                    return True
                                else:
                                    self.update_download_progress(download_id, 0.0, 0, 0, f"Error:{r3.status}")
                                    try:
                                        self.app.save_downloads_state(force=True)
                                    except Exception:
                                        pass
                                    return False
                else:
                    self.update_download_progress(download_id, 0.0, 0, 0, f"Error:{status}")
                    try:
                        self.app.save_downloads_state(force=True)
                    except Exception:
                        pass
                    return False
                try:
                    for d in self.app.downloads:
                        if d.get("id") == download_id:
                            d["filepath"] = str(filepath)
                            d["total_size"] = total_size if total_size is not None else 0
                            d["downloaded_bytes"] = downloaded
                            d["status"] = "Downloading"
                            break
                except Exception:
                    pass

                start_time = time.time()
                chunk_size = 256 * 1024  # 256KB for throughput
                ema_speed = None
                ema_alpha = 0.2
                last_t = start_time
                bytes_window = 0
                async with aiofiles.open(filepath, open_mode) as file:
                    idx = 0
                    async for chunk in response.content.iter_chunked(chunk_size):
                        if not chunk:
                            await asyncio.sleep(0)
                            continue
                        await file.write(chunk)
                        downloaded += len(chunk)
                        bytes_window += len(chunk)

                        # progress
                        progress = (downloaded / total_size) if (total_size and total_size > 0) else 0
                        now = time.time()
                        dt = now - last_t
                        inst_speed = (bytes_window / dt) if dt > 0 else 0
                        bytes_window = 0
                        last_t = now
                        if ema_speed is None:
                            ema_speed = inst_speed
                        else:
                            ema_speed = ema_alpha * inst_speed + (1 - ema_alpha) * ema_speed
                        speed = ema_speed or 0
                        eta = ((total_size - downloaded) / speed) if (total_size and speed > 0) else 0
                        try:
                            for d in self.app.downloads:
                                if d.get("id") == download_id:
                                    d["downloaded_bytes"] = downloaded
                                    if total_size:
                                        d["total_size"] = total_size
                                    d["_smoothed_bps"] = speed
                                    break
                        except Exception:
                            pass

                        self.update_download_progress(download_id, progress, speed, eta, "Downloading")
                        idx += 1
                        if (idx % 8) == 0:
                            await asyncio.sleep(0)

                if total_size and downloaded >= total_size:
                    self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                else:
                    self.update_download_progress(download_id, 1.0, 0, 0, "Completed")
                try:
                    self.app.save_downloads_state(force=True)
                except Exception:
                    pass
                return True
        except asyncio.CancelledError:
            try:
                d = next((x for x in self.app.downloads if x.get("id") == download_id), None)
                if d:
                    total = int(d.get("total_size") or 0)
                    done = int(d.get("downloaded_bytes") or 0)
                    progress = (done / total) if total else d.get("progress", 0.0)
                    self.update_download_progress(download_id, progress, 0, 0, "Paused")
                    self.app.save_downloads_state(force=True)
            except Exception:
                pass
            return False
        except Exception as e:
            logging.exception(f"[TermoLoad] download_file exception id={download_id}: {e}")
            self.update_download_progress(download_id, 0, 0, 0, f"Error:{str(e)}")
            try:
                self.app.save_downloads_state(force=True)
            except Exception:
                pass
            return False
    def update_download_progress(self,download_id:int,progress:float,speed:float,eta:float,status:str):
        for i, download in enumerate(self.app.downloads):
            if download["id"] == download_id:
                logging.debug(f"[TermoLoad] update progress id={download_id} {int(progress*100)}% status={status}")
                download["progress"] = progress
                download["speed"] = self.format_speed(speed)
                download["eta"] = self.format_time(eta)
                prev_status = download.get("status")
                download["status"] = status
                
                try:
                    if status == "Completed" and prev_status != "Completed":
                        self.app.history.add_entry(download, "completed")
                    elif status.startswith("Error") and not prev_status.startswith("Error"):
                        self.app.history.add_entry(download, "failed")
                except Exception:
                    pass

                try:
                    if status == "Completed" and prev_status != "Completed":
                        self.app._play_completion_sound()
                    elif status.startswith("Error") and not prev_status.startswith("Error"):
                        self.app._play_error_sound()
                except Exception:
                    pass
                
                try:
                    if status == "Downloading":
                        self.app._previous_had_active = True
                        self.app._shutdown_triggered = False
                except Exception:
                    pass
                break
    def format_speed(self,bytes_per_second:float)-> str:
        if bytes_per_second == 0:
            return "0 B/s"
        elif bytes_per_second < 1024:
            return f"{bytes_per_second:.1f} B/s"
        elif bytes_per_second < 1024**2:
            return f"{bytes_per_second/1024:.1f} KB/s"
        elif bytes_per_second < 1024**3:
            return f"{bytes_per_second/(1024**2):.1f} MB/s"
        else:
            return f"{bytes_per_second/(1024**3):.1f} GB/s"
        
    def format_time(self,seconds:float)-> str:
        if seconds == 0 or seconds == float('inf'):
            return "0s"
        elif seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds//60)}m {int(seconds%60)}s"
        else:
            return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"
        
    @staticmethod
    def is_video_url(url: str) -> bool:
        try:
            host = urlparse(url).netloc.lower()
            return any(h in host for h in ("youtube.com", "youtu.be", "m.youtube.com", "youtube-nocookie.com"))
        except Exception:
            return False
    
    @staticmethod
    def extract_magnet_name(magnet_url: str) -> Optional[str]:
        """Extract display name from magnet link.
        Parses the dn (display name) parameter from magnet URI.
        Returns None if not found or not a magnet link.
        """
        try:
            if not magnet_url.startswith("magnet:"):
                return None
            
            # Parse the magnet URL to extract the dn parameter
            from urllib.parse import parse_qs, unquote
            
            # Split on ? to get the query part
            if "?" not in magnet_url:
                return None
            
            query_part = magnet_url.split("?", 1)[1]
            params = parse_qs(query_part)
            
            # Get the dn (display name) parameter
            if "dn" in params and params["dn"]:
                display_name = unquote(params["dn"][0])
                # Clean up the name - replace + with spaces and decode
                display_name = display_name.replace("+", " ")
                return display_name.strip()
            
            # If no dn parameter, try to extract hash as fallback
            if "xt" in params and params["xt"]:
                xt = params["xt"][0]
                if ":" in xt:
                    hash_value = xt.split(":")[-1]
                    return f"torrent_{hash_value[:8]}"
            
            return None
        except Exception:
            return None
    
    def update_torrent_peers(self, download_id: int, peers: int, seeds: int) -> None:
        """Update peer and seed count for a torrent download.
        This will be called by the torrent engine once implemented.
        """
        try:
            for d in self.app.downloads:
                if d.get("id") == download_id and d.get("type") == "Torrent":
                    d["peers"] = peers
                    d["seeds"] = seeds
                    logging.debug(f"[TermoLoad] Updated torrent {download_id}: {peers} peers, {seeds} seeds")
                    break
        except Exception:
            logging.exception(f"[TermoLoad] Failed to update peer/seed count for torrent {download_id}")
    
class AddDownloadModal(ModalScreen[dict]):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal_container"):
            yield Static("Add New Download",id="modal_title")
            yield Label("Enter URL or Torrent File Path:")
            yield Input(id="download_input", placeholder="Enter URL or path...")
            with Horizontal():
                yield Button("Browse File", id="browse_file", variant="default")
            yield Label("Save to folder:")
            yield Input(
                id="save_path",
                placeholder="Leave empty for default (download folder)",
                value="downloads"
            )
            with Horizontal():
                yield Button("Browse",id ="browse_folder",variant="default")
            with Horizontal():
                yield Button("Add", id="confirm_add", variant="success")
                yield Button("Cancel", id="cancel_add", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_add":
            url_widget = self.query_one("#download_input", Input)
            path_widget = self.query_one("#save_path", Input)

            url = url_widget.value.strip()
            save_path = path_widget.value.strip() or "downloads"

            logging.info(f"[TermoLoad] AddDownloadModal: user entered url={url} save_path={save_path}")

            if url:
                try:
                    app = self.app
                    if hasattr(app, 'process_modal_result'):
                        app.process_modal_result({'url': url, 'path': save_path})
                except Exception:
                    pass
                self.dismiss({"url":url,"path":save_path})
            else:
                self.dismiss(None)
        elif event.button.id == "cancel_add":
            self.dismiss(None)

        elif event.button.id == "browse_file":
            # Run dialog in background to prevent hanging
            async def browse_file():
                try:
                    file_path = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: TkinterDialogHelper.ask_open_filename(
                            title="Select Torrent File",
                            filetypes=[("Torrent Files", "*.torrent"), ("All Files", "*.*")]
                        )
                    )
                    if file_path:
                        url_widget = self.query_one("#download_input", Input)
                        url_widget.value = file_path
                except Exception as e:
                    logging.exception(f"[AddDownloadModal] Browse file error: {e}")
            
            asyncio.create_task(browse_file())
        
        elif event.button.id == "browse_folder":
            # Run dialog in background to prevent hanging
            async def browse_folder():
                try:
                    folder = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: TkinterDialogHelper.ask_directory(title="Select Download Folder")
                    )
                    if folder:
                        path_widget = self.query_one("#save_path", Input)
                        path_widget.value = folder
                except Exception as e:
                    logging.exception(f"[AddDownloadModal] Browse folder error: {e}")
            
            asyncio.create_task(browse_folder())

class PathSelectModel(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal_container"):
            yield Static("Select Download Location ", id = "modal_title")
            yield Label("Choose where to save the file:")
            yield Input(
                    id="path_input", 
                    placeholder="e.g., C:\\Downloads\\MyFiles or leave empty for default",
                    value=str(Path("Downloads"))
                )
            
            with Horizontal():
                yield Button("Browse", id="browse_btn", variant="default")
                yield Button("OK", id="confirm_path", variant="success")
                yield Button("Cancel", id="cancel_path", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_path":
            input_widget = self.query_one("#path_input", Input)
            path = input_widget.value.strip()
            self.dismiss(path)
        elif event.button.id == "cancel_path":
            self.dismiss(None)
        elif event.button.id == "browse_btn":
            # Run dialog in background to prevent hanging in EXE
            async def browse_folder():
                try:
                    folder = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: TkinterDialogHelper.ask_directory(title="Select Download Folder")
                    )
                    if folder:
                        path_widget = self.query_one("#path_input", Input)
                        path_widget.value = folder
                except Exception as e:
                    logging.exception(f"[PathSelectModel] Browse error: {e}")
            
            asyncio.create_task(browse_folder())

class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal dialog to confirm file deletion."""
    
    def __init__(self, download_name: str):
        super().__init__()
        self.download_name = download_name
    
    def compose(self) -> ComposeResult:
        with Vertical(id="modal_container"):
            yield Static("⚠️ Confirm Delete + Remove", id="modal_title")
            yield Static(f"Are you sure you want to DELETE the files and remove from list?", classes="confirm_message")
            yield Static(f"Download: {self.download_name}", classes="confirm_details")
            yield Static("This will permanently delete files from disk!", classes="confirm_warning")
            
            with Horizontal():
                yield Button("Cancel", id="confirm_cancel", variant="default")
                yield Button("Delete + Remove", id="confirm_delete", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_delete":
            self.dismiss(True)
        elif event.button.id == "confirm_cancel":
            self.dismiss(False) 
class TorrentFileSelectModal(ModalScreen[dict]):
    def __init__(self,torrent_info:dict):
        super().__init__()
        self.torrent_info = torrent_info
        self.file_checkboxes = []
    
    def compose(self) -> ComposeResult:
        with Vertical(id="modal_container"):
            yield Static("Select Files to Download", id="modal_title")
            yield Static(f"Torrent: {self.torrent_info.get('name','Unknown')}", classes="torrent_name")

            total_size = self.torrent_info.get("total_size",0)
            size_str = self.format_size(total_size)
            yield Static(f"Total Size: {size_str} | Files: {len(self.torrent_info.get('files', []))}", classes="torrent_info")

            with Vertical(id="file_list_container"):
                yield Static("Select the files you want to download:", classes="file_list_header")
            
                for idx, file_info in enumerate(self.torrent_info.get('files', [])):
                    file_path = file_info.get('path', f'file_{idx}')
                    file_size = file_info.get('size', 0)
                    size_str = self._format_size(file_size)

                    with Horizontal(classes="file_item"):
                        cb = Checkbox(f"{file_path} ({size_str})", id=f"file_cb_{idx}", value=True)
                        yield cb
                        self.file_checkboxes.append(cb)

            with Horizontal(classes="selection_buttons"):
                yield Button("Select All", id="select_all", variant="default")
                yield Button("Deselect All", id="deselect_all", variant="default")
            
            with Horizontal():
                yield Button("Cancel", id="cancel_select", variant="error")
                yield Button("Download Selected", id="confirm_select", variant="success")
    
    def _format_size(self,size_bytes:int)-> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select_all":
            for cb in self.file_checkboxes:
                cb.value = True
            return
    
        elif event.button.id == "deselect_all":
            for cb in self.file_checkboxes:
                cb.value = False
            return
        
        elif event.button.id == "confirm_select":
            selected_files = []
            for idx, cb in enumerate(self.file_checkboxes):
                if cb.value:
                    selected_files.append(idx)
            
            if not selected_files:
                self.app.notify("Please select at least one file to download", severity="warning")
                return
            
            self.dismiss({
                "selected_files": selected_files,
                "torrent_info": self.torrent_info
            })
        elif event.button.id == "cancel_select":
            self.dismiss(None)


class LoadingScreen(App):
    """Beautiful loading/splash screen for TermoLoad"""
    
    CSS = """
    Screen {
        align: center middle;
        background: $surface;
    }
    
    #loading_container {
        width: 60;
        height: 20;
        border: thick $primary;
        background: $surface;
        align: center middle;
        padding: 2;
    }
    
    #logo {
        text-align: center;
        color: $accent;
        text-style: bold;
        padding: 1;
    }
    
    #tagline {
        text-align: center;
        color: $text;
        padding: 1;
    }
    
    #spinner {
        text-align: center;
        color: $primary;
        text-style: bold;
        padding: 1;
    }
    
    #status {
        text-align: center;
        color: $text-muted;
        padding: 1;
    }
    
    #version {
        text-align: center;
        color: $text-muted;
        padding: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0
        self.initialization_complete = False
        
    def compose(self) -> ComposeResult:
        with Container(id="loading_container"):
            yield Static(self._get_logo(), id="logo")
            yield Static("Terminal-Based Download Manager", id="tagline")
            yield Static(self.spinner_frames[0], id="spinner")
            yield Static("Initializing application...", id="status")
            yield Static("v1.0", id="version")
    
    def _get_logo(self) -> str:
        return """
╔╦╗╔═╗╦═╗╔╦╗╔═╗╦  ╔═╗╔═╗╔╦╗
 ║ ║╣ ╠╦╝║║║║ ║║  ║ ║╠═╣ ║║
 ╩ ╚═╝╩╚═╩ ╩╚═╝╩═╝╚═╝╩ ╩═╩╝
        """
    
    async def on_mount(self) -> None:
        """Start the loading animation"""
        self.set_interval(0.1, self._update_spinner)
        self.set_timer(0.5, self._update_status_initializing)
        self.set_timer(1.0, self._update_status_loading_modules)
        self.set_timer(1.5, self._update_status_preparing)
        self.set_timer(2.0, self._complete_loading)
    
    def _update_spinner(self) -> None:
        """Animate the spinner"""
        if not self.initialization_complete:
            self.current_frame = (self.current_frame + 1) % len(self.spinner_frames)
            spinner = self.query_one("#spinner", Static)
            spinner.update(self.spinner_frames[self.current_frame])
    
    def _update_status_initializing(self) -> None:
        status = self.query_one("#status", Static)
        status.update("Initializing download manager...")
    
    def _update_status_loading_modules(self) -> None:
        status = self.query_one("#status", Static)
        status.update("Loading modules and dependencies...")
    
    def _update_status_preparing(self) -> None:
        status = self.query_one("#status", Static)
        status.update("Preparing interface...")
    
    def _complete_loading(self) -> None:
        """Mark loading as complete and prepare to exit"""
        status = self.query_one("#status", Static)
        status.update("Ready! ✓")
        spinner = self.query_one("#spinner", Static)
        spinner.update("✓")
        self.initialization_complete = True
        self.set_timer(0.5, self.exit)
            
class TermoLoad(App):
    BINDINGS = [("q", "quit", "Quit"),("a","add_download","Add Download"),("m","minimize_to_tray","Minimize to Tray"),("o","open_folder","Open Folder")]

    CSS = """
    AddDownloadModal {
        align: center middle;
        }
    
    ConfirmDeleteModal {
        align: center middle;
        }
    
    .confirm_message {
        text-align: center;
        padding: 1;
        color: $text;
    }
    
    .confirm_details {
        text-align: center;
        padding: 0 1 1 1;
        color: $accent;
        text-style: bold;
    }
    
    .confirm_warning {
        text-align: center;
        padding: 1;
        color: $error;
        text-style: bold;
    }
    
    #history_panel{
        height: 100%;
        width: 100%;
        padding: 1 2;
        background: $surface;
    }

    #history_title{
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    #history_toolbar{
        padding: 0 0 1 0;
    }

    #history_toolbar Button{
        margin-right: 1;
    }
    
    #history_table{
        height: 1fr;
    }

    #stats_panel{
        height: 100%;
        width: 100%;
        padding: 1 2;
        background: $surface;
        overflow-y: auto;
    }


    #stats_title{
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }
    
    #stats_content{
        padding: 1;
        color: $text;
    }

    #modal_container{
        width: 45%;
        height: 70%;
        min-height: 12;
        background: $surface;
        border: thick $primary;
        padding: 1;
        }

    #modal_title{
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        }
    
    #main{
        height: 100%;
        padding: 0;
        margin: 0;
    }
    #navbar{
        height: auto;
        padding: 0 1;
    }
    #no_downloads{
        padding: 1 2;
        color: $text-muted;
    }
    #downloads_table{
        height: 1fr;
        min-height: 20;
        width: 100%;
    }
    #downloads_toolbar {
        padding: 0 1 1 1;
    }
    #downloads_toolbar Button {
        margin-right: 1;
    }
    #status_info{
        padding: 0 1;
        color: $warning;
    }
    #settings_panel{
        height: 100%;
        width: 100%;
        overflow: auto;
        padding: 1 2;
        background: $surface;
    }
    /* improve button visibility and spacing in settings */
    #settings_panel Button{
        padding: 0 2;
        min-width: 14;
        color: $text;
    }
    #settings_panel Horizontal{
        align: left middle;
        padding-bottom: 1;
    }
    #settings_panel Input{
        width: 100%;
        min-height: 3;
    }
    #settings_panel Horizontal Input{
        width: 1fr;
    }
    #settings_panel Horizontal Button{
        margin-right: 1;
        background: $boost;
    }
    #settings_panel Checkbox{
        margin: 1 0;
        padding: 0 1;
    }
    #settings_panel > Horizontal:last-child {
        margin-top: 2;
        padding-top: 1;
        border-top: solid $primary;
    }
    /* Modal browse buttons - highlighted with spacing */
    #modal_container Horizontal {
        padding-bottom: 1;
    }
    #modal_container Input {
        margin-right: 1;
    }
    #browse_file, #browse_folder {
        background: $accent;
        color: $text;
        border: tall $primary;
        min-width: 12;
    }
    #browse_file:hover, #browse_folder:hover {
        background: $accent-darken-1;
    }
    #help_panel{
        height: 100%;
        width: 100%;
        overflow-y: auto;
        overflow-x: auto;
        scrollbar-size: 2 1;
        padding: 1 2;
        background: $surface;
        text-style: none;
        color: $text;
    }
    #logs_panel{
        height: 100%;
        width: 100%;
        overflow-y: auto;
        padding: 1 2;
        background: $surface;
    }
    .torrent_name {
        text-align: center;
        padding: 0 1 1 1;
        color: $accent;
        text-style: bold;
    }
    
    .torrent_info {
        text-align: center;
        padding: 0 1 1 1;
        color: $text-muted;
    }
    
    .file_list_header {
        padding: 1 0;
        color: $text;
        text-style: bold;
    }
    #file_list_container {
        height: 30;
        overflow-y: auto;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    .file_item {
        padding: 0 0 1 0;
        align: left middle;
    }
    
    .file_item Checkbox {
        width: 100%;
    }
    
    .selection_buttons {
        padding: 0 0 1 0;
    }
    
    .selection_buttons Button {
        margin-right: 1;
    }
    
    """
    
    def __init__(self):
        super().__init__()
        self.downloader = RealDownloader(self)
        self.download_tasks={}
        self.tray_icon = None
        self.tray_thread = None
        self._minimized_to_tray = False
        self.history= DownloadHistory(self)
        # Help panel scrolling fallback when ScrollView isn't available
        self._help_text_lines: List[str] = []
        self._help_scroll: int = 0
        # Track user interaction to prevent table updates from interfering
        self._user_interacting = False
        self._last_interaction_time = 0
        
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True) 

        with Horizontal(id="navbar"):
            yield Button("+ Add Download", id="btn_add", variant="success")
            yield Button("Downloads", id="btn_downloads", variant="primary")
            yield Button("History", id="btn_history")
            yield Button("Stats", id="btn_stats")
            yield Button("Settings", id="btn_settings")
            yield Button("Logs", id="btn_logs")
            yield Button("Help", id="btn_help")
            yield Button ("Minimize",id = "btn_minimize", variant="default")

        with Container(id="main"):
            # Downloads section at the top - shown by default
            yield Static("No downloads yet. Press 'a' or + Add Download to create one.", id="no_downloads")
            with Horizontal(id="downloads_toolbar"):
                yield Button("Pause Selected", id="btn_pause_sel")
                yield Button("Resume Selected", id="btn_resume_sel")
                yield Button("Pause All", id="btn_pause_all")
                yield Button("Resume All", id="btn_resume_all")
                yield Button("Remove From List", id="button_remove_list")
                yield Button("Delete + Remove",id="btn_delete_and_remove", variant="error")
            yield DataTable(id="downloads_table")
            yield Static("", id="status_info")
            
            # Other panels below (hidden by default)
            with Vertical(id="settings_panel"):
                yield Static("⚙️ Settings", id="settings_title")
                yield Label("Default download folder:")
                with Horizontal():
                    yield Input(id="settings_download_folder", placeholder="e.g., C:\\Users\\You\\Downloads")
                    yield Button("Browse", id="settings_browse", variant="default")
                yield Label("Concurrent downloads:")
                yield Input(id="settings_concurrent", placeholder="3")
                yield Label("Max download speed (KB/s, 0 = unlimited):")
                yield Input(id="settings_speed", placeholder="0")
                yield Checkbox("Shutdown PC when all downloads complete (WARNING: Real shutdown!)", id="settings_shutdown")
                yield Checkbox("Play sound on download completion", id="settings_sound_complete")
                yield Checkbox("Play sound on download error", id="settings_sound_error")
                
                with Horizontal():
                    yield Button("Cancel", id="settings_cancel", variant="default")
                    yield Button("Save Settings", id="settings_save", variant="primary")

            with Vertical(id="history_panel"):
                yield Static("📜 Download History", id="history_title")
                with Horizontal(id="history_toolbar"):
                    yield Button("Clear History", id="btn_clear_history", variant="error")
                    yield Button("Export CSV", id="btn_export_csv", variant="default")
                yield DataTable(id="history_table")

            with Vertical(id="stats_panel"):
                yield Static("📊 Download Statistics", id="stats_title")
                yield Static("",id="stats_content")

            yield Static("📜 Logs will go here", id="logs_panel")
            # Use ScrollView if available (some textual versions expose it in different modules)
            if ScrollView is not None:
                yield ScrollView(id="help_panel")
            else:
                yield Static("❓ Help/About here", id="help_panel")

        yield Footer()
    
    def _create_tray_icon_image(self):
        # Lazy load PIL modules
        Image, ImageDraw = get_pil_modules()
        
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        dc.rectangle([20,15,44,25], fill="#00ff00")
        dc.polygon([(32,25),(20,35),(44,35)], fill="#00ff00")
        dc.rectangle([28,25,36,45], fill="#00ff00")
        dc.rectangle([20,45,44,50], fill="#00ff00")

        return image

    def _play_completion_sound(self):
        """Play a sound when a download completes successfully."""
        if not self.settings.get("sound_on_complete", True):
            return
        
        def _play():
            try:
                play_notification_sound(800, 150, 'info')
                time.sleep(0.05)
                play_notification_sound(1000, 200, 'complete')
            except Exception:
                logging.debug("[TermoLoad] Failed to play completion sound")
        
        threading.Thread(target=_play, daemon=True).start()
    
    def _play_error_sound(self):
        if not self.settings.get("sound_on_error", True):
            return
        
        def _play():
            try:
                play_notification_sound(500, 200, 'error')
                time.sleep(0.05)
                play_notification_sound(300, 250, 'error')
            except Exception:
                logging.debug("[TermoLoad] Failed to play error sound")
        
        threading.Thread(target=_play, daemon=True).start()
    def action_open_folder(self) -> None:
        """Open the folder containing the downloaded file."""
        try:
            d = self._get_selected_download()
            if not d:
                self.notify("No download selected to open folder.", severity="warning")
                return
            
            filepath = self._resolve_download_path(d)
            if not filepath or not filepath.exists():
                self.notify("Downloaded file not found.", severity="error")
                logging.warning(f"[TermoLoad] File not found to open folder: {filepath}")
                return

            folder_path = filepath.parent
            
            # Use threading to prevent UI blocking
            def open_folder_thread():
                try:
                    if sys.platform == 'win32':
                        # Use Windows explorer to select the file
                        subprocess.Popen(['explorer', '/select,', str(filepath)], 
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                        logging.info(f"[TermoLoad] Opened folder (Windows): {folder_path}")
                    elif sys.platform == 'darwin':
                        subprocess.Popen(['open', '-R', str(filepath)])
                        logging.info(f"[TermoLoad] Opened folder (macOS): {folder_path}")
                    else:
                        subprocess.Popen(['xdg-open', str(folder_path)])
                        logging.info(f"[TermoLoad] Opened folder (Linux): {folder_path}")
                except Exception as e:
                    logging.exception(f"[TermoLoad] Failed to open folder {folder_path}: {e}")
            
            # Run in separate thread to prevent blocking
            thread = threading.Thread(target=open_folder_thread, daemon=True)
            thread.start()
            
            self.notify(f"Opening folder: {folder_path.name}", severity="information")
           
        except Exception as e:
            logging.exception(f"[TermoLoad] action_open_folder exception: {e}")
            self.notify("Failed to open folder", severity="error")

    def _safe_update_table_cell(self, row_key, col, value):
        """Safely update a table cell with error handling to prevent crashes."""
        try:
            if self.downloads_table and hasattr(self.downloads_table, 'update_cell'):
                self.downloads_table.update_cell(row_key, col, value)
        except Exception as e:
            logging.debug(f"[TermoLoad] Failed to update table cell [{row_key}, {col}]: {e}")
            # Don't crash on table update errors
            pass
    
    def _safe_add_table_row(self, *args):
        """Safely add a row to the table with error handling to prevent crashes."""
        try:
            if self.downloads_table and hasattr(self.downloads_table, 'add_row'):
                return self.downloads_table.add_row(*args)
        except Exception as e:
            logging.debug(f"[TermoLoad] Failed to add table row: {e}")
            return len(self.downloads)

    def _setup_tray_icon(self):
        try:
            pystray = get_pystray()
        except Exception:
            logging.warning("[TermoLoad] pystray not installed, system tray icon disabled")
            return
        
        try:
            icon_image = self._create_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Show TermoLoad", self._restore_from_tray, default=True),
                pystray.MenuItem("Active Downloads", lambda: self._show_active_count()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit_from_tray)
            )
            self.tray_icon = pystray.Icon(
                "TermoLoad",
                icon_image,
                "TermoLoad",
                menu)
        except Exception:
            logging.exception("[TermoLoad] Failed to create system tray icon")

    def _show_active_count(self):
        try:
            active = [d for d in self.downloads if d.get("status") == "Downloading"]
            completed = [d for d in self.downloads if d.get("status") == "Completed"]
            
            if self.tray_icon:
                self.tray_icon.notify(
                    f"Active:{len(active)} | Completed:{len(completed)}",
                    "TermoLoad Status"
                )
        except Exception:
            logging.exception("[TermoLoad] Failed to show active count")
    
    def minimize_to_tray(self):
        # Lazy load pystray
        try:
            pystray = get_pystray()
        except Exception:
            logging.warning("[TermoLoad] pystray not installed, cannot minimize to tray")
            return
        
        try:
            if not self.tray_icon:
                self._setup_tray_icon()
            
            if self.tray_icon and not self._minimized_to_tray:
                self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=False)
                self.tray_thread.start()
                self._minimized_to_tray = True
                logging.info("[TermoLoad] Minimized to system tray")
                
                if sys.platform == 'win32':
                    try:
                        # Get console window handle
                        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                        if hwnd:
                            # Hide from taskbar by removing WS_EX_APPWINDOW and adding WS_EX_TOOLWINDOW
                            GWL_EXSTYLE = -20
                            WS_EX_APPWINDOW = 0x00040000
                            WS_EX_TOOLWINDOW = 0x00000080
                            
                            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                            style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
                            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                            
                            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
                    except Exception as e:
                        logging.warning(f"[TermoLoad] Failed to hide console window: {e}")
                
                self.exit()
        except Exception:
            logging.exception("[TermoLoad] Failed to minimize to tray")

    def _restore_from_tray(self, icon=None, item=None):
        try:
            if self.tray_icon:
                self.tray_icon.stop()
                self._minimized_to_tray = False
            
            if sys.platform == 'win32':
                try:
                    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                    if hwnd:
                        # Restore taskbar visibility by adding WS_EX_APPWINDOW
                        GWL_EXSTYLE = -20
                        WS_EX_APPWINDOW = 0x00040000
                        WS_EX_TOOLWINDOW = 0x00000080
                        
                        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                        style = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
                        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                        
                        # Show and activate the window
                        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                except Exception as e:
                    logging.warning(f"[TermoLoad] Failed to show console window: {e}")
            
            logging.info("[TermoLoad] Restoring from tray")
            python = sys.executable
            os.execv(python, [python] + sys.argv)
            
        except Exception:
            logging.exception("[TermoLoad] Failed to restore from tray")

    def _quit_from_tray(self, icon=None, item=None):
        try:
            logging.info("[TermoLoad] Quitting from tray")
            for task in self.download_tasks.values():
                if not task.done():
                    task.cancel()
            try:
                for d in self.downloads:
                    if d.get("status") == "Downloading":
                        d["status"] = "Paused"
                self.save_downloads_state(force=True)
            except Exception:
                pass

            if self.tray_icon:
                self.tray_icon.stop()

            sys.exit(0)
        except Exception:
            logging.exception("[TermoLoad] Failed to quit from tray")
    
    def action_minimize_to_tray(self) -> None:
        self.minimize_to_tray()

                

    def populate_history_table(self):
        try:
            self.history_table.clear()

            for entry in reversed(self.history.history):
                try:
                    date = entry.get("date", "Unknown")
                    name = entry.get("name", "Unknown")[:40]  # Truncate long names
                    dtype = entry.get("type", "Unknown")
                    size = entry.get("size", 0)
                    status = entry.get("status", "unknown")

                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024**2:
                        size_str = f"{size/1024:.1f} KB"
                    elif size < 1024**3:
                        size_str = f"{size/(1024**2):.1f} MB"
                    else:
                        size_str = f"{size/(1024**3):.1f} GB"

                    status_map = {
                        "completed": "✅ Completed",
                        "failed": "❌ Failed",
                        "cancelled": "⏸️ Cancelled"
                    }

                    staus_display = status_map.get(status, status)

                    self.history_table.add_row(date,
                                                name,
                                                dtype,
                                                size_str,
                                                staus_display
                                                
                    )
                except Exception:
                    logging.exception("[TermoLoad] Failed to add history entry to table")

        except Exception:
            logging.exception("[TermoLoad] Failed to populate history table")

    
    def build_stats_display(self) -> str:
        try:
            stats = self.history.get_statistics()

            lines = []
            lines.append("📊 Overall Statistics\n" + "="*50)
            lines.append(f"Total Downloads: {stats.get('total_downloads', 0)}")
            lines.append(f"✅ Completed: {stats.get('completed', 0)}")
            lines.append(f"❌ Failed: {stats.get('failed', 0)}")
            lines.append(f"⏸️ Cancelled: {stats.get('cancelled', 0)}")
            lines.append(f"Success Rate: {stats.get('success_rate', 0):.1f}%")
            lines.append("")
            lines.append("📁 Data Transferred\n" + "="*50)
            total_size = stats.get('total_size', 0)
            total_dl = stats.get('total_downloaded', 0)

            if total_size < 1024**3:
                lines.append(f"Total Downloaded (Completed): {total_size/(1024**2):.1f} MB")
            else:
                lines.append(f"Total Downloaded (Completed): {total_size/(1024**3):.2f} GB")
            
            if total_dl < 1024**3:
                lines.append(f"Total Downloaded (All): {total_dl/(1024**2):.1f} MB")
            else:
                lines.append(f"Total Downloaded (All): {total_dl/(1024**3):.2f} GB")
            
            lines.append("")

            lines.append("📁 By Type\n" + "="*50)
            by_type = stats.get('by_type', {})
            for dtype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"{dtype}: {count} downloads")
            
            lines.append("")
            lines.append("🕐 Recent Activity\n" + "="*50)
            lines.append(f"Last 7 days: {stats.get('recent_week', 0)} downloads")

            active = len([d for d in self.downloads if d.get("status") == "Downloading"])
            completed_session = len([d for d in self.downloads if d.get("status") == "Completed"])
            lines.append(f"\nCurrent Session:")
            lines.append(f"Active Downloads: {active}")
            lines.append(f"Completed Downloads: {completed_session}")
            lines.append(f"Total: {len(self.downloads)}")

            return "\n".join(lines)
        except Exception:
            logging.exception("[TermoLoad] Failed to build stats display")
            return "Failed to load statistics."
    
    def export_history_csv(self):
        """Export download history to CSV file"""
        async def do_export():
            try:
                import csv
                
                # Use async executor to prevent hanging in EXE
                filepath = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: TkinterDialogHelper.ask_save_filename(
                        title="Export History",
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                    )
                )
                
                if not filepath:
                    return
                
                # Add .csv extension if not present
                if not filepath.lower().endswith('.csv'):
                    filepath += '.csv'
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Date", "Name", "Type", "Size (bytes)", "Status", "URL", "Error"])
                    
                    for entry in self.history.history:
                        writer.writerow([
                            entry.get("date", ""),
                            entry.get("name", ""),
                            entry.get("type", ""),
                            entry.get("size", 0),
                            entry.get("status", ""),
                            entry.get("url", ""),
                            entry.get("error", "")
                        ])
                
                self.notify(f"History exported successfully", severity="information", timeout=5)
                logging.info(f"[TermoLoad] History exported to {filepath}")
            except Exception:
                logging.exception("[TermoLoad] Failed to export history")
                self.notify("Failed to export history", severity="error")
        
        asyncio.create_task(do_export())
    
    async def on_mount(self) -> None:
        self.downloads_table = self.query_one("#downloads_table", DataTable)
        self.downloads_toolbar = self.query_one("#downloads_toolbar", Horizontal)
        self.settings_panel = self.query_one("#settings_panel", Vertical)
        self.logs_panel = self.query_one("#logs_panel", Static)
        if ScrollView is not None:
            self.help_panel = self.query_one("#help_panel", ScrollView)
        else:
            self.help_panel = self.query_one("#help_panel", Static)
        self.status_info = self.query_one("#status_info", Static)
        self.no_downloads = self.query_one("#no_downloads", Static)
        self.history_panel = self.query_one("#history_panel", Vertical)
        self.history_table = self.query_one("#history_table", DataTable)
        self.stats_panel = self.query_one("#stats_panel", Vertical)
        self.stats_content = self.query_one("#stats_content", Static)

        self.settings_panel.visible = False
        self.settings_panel.display = False
        self.logs_panel.visible = False
        self.logs_panel.display = False
        self.help_panel.visible = False
        self.help_panel.display = False
        self.no_downloads.visible = True
        self.no_downloads.display = True
        self.downloads_toolbar.visible = False
        self.downloads_toolbar.display = False
        self.downloads_table.visible = False
        self.downloads_table.display = False
        self.status_info.visible = False
        self.status_info.display = False
        self.history_panel.visible = False
        self.history_panel.display = False
        self.stats_panel.visible = False
        self.stats_panel.display = False

        self.downloads_table.add_columns("ID", "Type", "Name", "Progress", "Speed","Peers/Seeds", "Status", "ETA")
        self.history_table.add_columns("Date", "Name", "Type", "Size", "Status")
        try:
            self.downloads_table.cursor_type = "row"
            self.downloads_table.show_cursor = True
        except Exception:
            pass

        try:
            self.load_settings()
        except Exception:
            logging.exception("[TermoLoad] failed to load settings")

        try:
            # Use the safe setter which handles ScrollView vs Static fallback
            self._set_help_text()
        except Exception:
            pass

        try:
            persisted = self.load_downloads_state()
        except Exception:
            persisted = []
        self.downloads = []
        try:
            for entry in persisted:
                d = {
                    "id": entry.get("id", len(self.downloads) + 1),
                    "type": entry.get("type", "URL"),
                    "name": entry.get("name", f"download_{len(self.downloads)+1}"),
                    "url": entry.get("url", ""),
                    "path": entry.get("path", self.settings.get("download_folder", str(Path.home()/"Downloads"))),
                    "progress": float(entry.get("progress", 0.0)),
                    "speed": entry.get("speed", "0 B/s"),
                    "status": entry.get("status", "Paused"),
                    "eta": entry.get("eta", "--"),
                    "downloaded_bytes": int(entry.get("downloaded_bytes", 0) or 0),
                    "total_size": int(entry.get("total_size", 0) or 0),
                    "filepath": entry.get("filepath", ""),
                    "peers": entry.get("peers", 0),
                    "seeds": entry.get("seeds", 0)
                }
                
                peers_seeds = "--"
                if d.get("type") == "Torrent":
                    peers = d.get("peers", 0)
                    seeds = d.get("seeds", 0)
                    if peers > 0 or seeds > 0:
                        peers_seeds = f"{peers}↓/{seeds}↑"
                    elif d.get("status") == "Pending":
                        peers_seeds = "Waiting..."
                    elif d.get("status") == "Downloading":
                        peers_seeds = "Connecting..."
                
                try:
                    rk = self.downloads_table.add_row(
                        str(d["id"]), d["type"], d["name"], f"{int(d['progress']*100)}%", d["speed"], peers_seeds, d["status"], d["eta"]
                    )
                except Exception:
                    rk = len(self.downloads)
                d["row_key"] = rk
                self.downloads.append(d)
        except Exception:
            logging.exception("[TermoLoad] Failed to rebuild table from persisted state")
        
        # Show/hide download widgets based on whether we have downloads (default view is Downloads tab if items exist)
        if len(self.downloads) > 0:
            self.downloads_table.visible = True
            self.downloads_table.display = True
            self.downloads_toolbar.visible = True
            self.downloads_toolbar.display = True
            self.status_info.visible = True
            self.status_info.display = True
            self.no_downloads.visible = False
            self.no_downloads.display = False
        
        self._shutdown_triggered = False
        self._previous_had_active = False
        try:
            self.set_interval(0.5, self.sync_table_from_downloads)
        except Exception:
            logging.exception("[TermoLoad] failed to set sync interval")
        try:
            await self._resume_incomplete_downloads()
        except Exception:
            logging.exception("[TermoLoad] Failed to resume incomplete downloads on startup")
        try:
            self.downloads_table.focus()
            if getattr(self.downloads_table, "row_count", 0) > 0:
                try:
                    self.downloads_table.cursor_row = 0
                except Exception:
                    pass
        except Exception:
            pass

    def load_settings(self):
        settings_path = Path("settings.json")
        
        # Get Windows Downloads folder: C:\Users\{username}\Downloads
        try:
            windows_downloads = Path.home() / "Downloads"
            if not windows_downloads.exists():
                windows_downloads.mkdir(parents=True, exist_ok=True)
            default_download_path = str(windows_downloads)
        except Exception:
            # Fallback to current directory/downloads if home path fails
            default_download_path = str(Path.cwd() / "downloads")
        
        defaults = {
            "download_folder": default_download_path,
            "concurrent": 3,
            "max_speed_kb": 0,
            "shutdown_on_complete": False,
            "sound_on_complete": True,
            "sound_on_error": True
        }
        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                logging.exception("[TermoLoad] failed to read settings.json, using defaults")
                self.settings = defaults
        else:
            self.settings = defaults
        try:
            soc = self.settings.get("shutdown_on_complete", False)
            if isinstance(soc, str):
                socv = soc.strip().lower()
                self.settings["shutdown_on_complete"] = socv in ("true", "1", "yes", "y")
            else:
                self.settings["shutdown_on_complete"] = bool(soc)
        except Exception:
            self.settings["shutdown_on_complete"] = False

        try:
            self.populate_settings_panel()
        except Exception:
            pass

    def save_settings(self):
        settings_path = Path("settings.json")
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            logging.info(f"[TermoLoad] settings saved to {settings_path}")
        except Exception:
            logging.exception("[TermoLoad] failed to save settings.json")

    def populate_settings_panel(self):
        try:
            folder_input = self.query_one("#settings_download_folder", Input)
            folder_input.value = str(self.settings.get("download_folder", "downloads"))
        except Exception:
            pass
        try:
            concurrent_input = self.query_one("#settings_concurrent", Input)
            concurrent_input.value = str(self.settings.get("concurrent", 3))
        except Exception:
            pass
        try:
            speed_input = self.query_one("#settings_speed", Input)
            speed_input.value = str(self.settings.get("max_speed_kb", 0))
        except Exception:
            pass
        try:
            shutdown_checkbox = self.query_one("#settings_shutdown", Checkbox)
            shutdown_checkbox.value = bool(self.settings.get("shutdown_on_complete", False))
        except Exception:
            pass
        try:
            sound_complete_checkbox = self.query_one("#settings_sound_complete", Checkbox)
            sound_complete_checkbox.value = bool(self.settings.get("sound_on_complete", True))
        except Exception:
            pass
        try:
            sound_error_checkbox = self.query_one("#settings_sound_error", Checkbox)
            sound_error_checkbox.value = bool(self.settings.get("sound_on_error", True))
        except Exception:
            pass

    async def sync_table_from_downloads(self):
        try:
            current_time = time.time()
            if self._user_interacting and (current_time - self._last_interaction_time) < 3.0:
                return
            else:
                self._user_interacting = False
            
            rebuild_needed = False
            selected_index = None
            selected_download_id = None
            try:
                if hasattr(self.downloads_table, "cursor_row") and self.downloads_table.cursor_row is not None:
                    selected_index = int(self.downloads_table.cursor_row)
                    if selected_index < len(self.downloads):
                        selected_download_id = self.downloads[selected_index].get("id")
            except Exception:
                selected_index = None
            
            # Try to update cells without rebuilding
            for i, d in enumerate(self.downloads):
                try:
                    row_key = d.get("row_key", i)
                    prog = max(0.0, min(1.0, float(d.get('progress', 0) or 0)))
                    pct = f"{prog*100:.2f}%"
                    dl = int(d.get('downloaded_bytes', 0) or 0)
                    total = int(d.get('total_size', 0) or 0)
                    def _fmt_bytes(n:int)->str:
                        if n < 1024:
                            return f"{n} B"
                        elif n < 1024**2:
                            return f"{n/1024:.1f} KB"
                        elif n < 1024**3:
                            return f"{n/(1024**2):.1f} MB"
                        else:
                            return f"{n/(1024**3):.1f} GB"
                    bar_w = 20
                    filled = int(round(prog * bar_w))
                    bar = f"[{('#'*filled).ljust(bar_w, '-')}]"
                    bytes_txt = f" ({_fmt_bytes(dl)}/{_fmt_bytes(total)})" if total > 0 else ""

                    eta_str = d.get("eta", "--")
                    status = d.get("status", "Queued")
                    peers = "--"
                    if d.get("type") == "Torrent":
                        peers = d.get("peers",0)
                        seeds = d.get("seeds",0)
                        if peers > 0 or seeds > 0:
                            peers_seeds = f"{peers}↓/{seeds}↑"
                        elif status == "Downloading":
                            peers_seeds = "Connecting..."
                        


                    if status == "Downloading" and eta_str and eta_str != '--':
                        pass
                    elif status == "Completed":
                        eta_str = "Done"
                    elif status == "Paused":
                        eta_str = "--"
                    elif status == "Queued":
                        eta_str = "Waiting"
                    elif status.startswith("Error"):
                        eta_str = "--"

                    try:
                        eta_secs = 0
                        parts = eta_str.split()
                        for part in parts:
                            if part.endswith('h'):
                                eta_secs += int(part[:-1]) * 3600
                            elif part.endswith('m'):
                                eta_secs += int(part[:-1]) * 60
                            elif part.endswith('s'):
                                eta_secs += int(part[:-1])
                        if eta_secs <= 5:
                            status = "Finishing"
                    except Exception:
                        pass
                    self.downloads_table.update_cell(row_key, 3, f"{bar} {pct}{bytes_txt}")
                    self.downloads_table.update_cell(row_key, 4, d.get('speed', '0 B/s'))
                    self.downloads_table.update_cell(row_key, 5, status)
                    self.downloads_table.update_cell(row_key, 6, eta_str)
                    self.downloads_table.update_cell(row_key, 5, peers_seeds)
                    self.downloads_table.update_cell(row_key, 6, status)
                    self.downloads_table.update_cell(row_key, 7, eta_str)
                except Exception:
                    rebuild_needed = True
                    break

            if rebuild_needed:
                try:
                    try:
                        self.downloads_table.clear()
                    except Exception:
                        try:
                            while self.downloads_table.row_count > 0:
                                self.downloads_table.remove_row(0)
                        except Exception:
                            pass

                    for d in self.downloads:
                        try:
                            prog = max(0.0, min(1.0, float(d.get('progress', 0) or 0)))
                            pct = f"{prog*100:.2f}%"
                            dl = int(d.get('downloaded_bytes', 0) or 0)
                            total = int(d.get('total_size', 0) or 0)
                            def _fmt_bytes(n:int)->str:
                                if n < 1024:
                                    return f"{n} B"
                                elif n < 1024**2:
                                    return f"{n/1024:.1f} KB"
                                elif n < 1024**3:
                                    return f"{n/(1024**2):.1f} MB"
                                else:
                                    return f"{n/(1024**3):.1f} GB"
                            bar_w = 20
                            filled = int(round(prog * bar_w))
                            bar = f"[{('#'*filled).ljust(bar_w, '-')}]"
                            bytes_txt = f" ({_fmt_bytes(dl)}/{_fmt_bytes(total)})" if total > 0 else ""
                            
                            eta_str = d.get('eta', '--')
                            status = d.get('status', 'Queued')
                            peers_seeds = "--"

                            if d.get("type") == "Torrent":
                                peers = d.get("peers",0)
                                seeds = d.get("seeds",0)
                                if peers > 0 or seeds > 0:
                                    peers_seeds = f"{peers}↓/{seeds}↑"
                                elif status == "Downloading":
                                    peers_seeds = "Connecting..."
                                elif status == "Pending":
                                    peers_seeds = "Waiting..."
                            
                            if status == "Completed":
                                eta_str = "Done"
                            elif status == "Paused":
                                eta_str = "--"
                            elif status == "Queued":
                                eta_str = "Waiting"
                            elif status.startswith("Error"):
                                eta_str = "--"
                            
                            rk = self.downloads_table.add_row(
                                str(d.get("id")),
                                d.get("type", ""),
                                d.get("name", ""),
                                f"{bar} {pct}{bytes_txt}",
                                d.get('speed', '0 B/s'),
                                peers_seeds,
                                status,
                                eta_str
                            )
                            d['row_key'] = rk
                        except Exception:
                            d['row_key'] = None
                    
                    # Restore selection based on download ID if possible, otherwise use index
                    try:
                        if selected_download_id is not None:
                            # Find the row with the selected download ID
                            for idx, dl in enumerate(self.downloads):
                                if dl.get("id") == selected_download_id:
                                    self.downloads_table.cursor_row = idx
                                    break
                        elif selected_index is not None and self.downloads_table.row_count:
                            idx = max(0, min(selected_index, self.downloads_table.row_count - 1))
                            self.downloads_table.cursor_row = idx
                    except Exception:
                        pass
                except Exception:
                    logging.exception("[TermoLoad] sync_table_from_downloads: failed to rebuild table rows")
            try:
                if hasattr(self, 'logs_panel') and self.logs_panel and getattr(self.logs_panel, 'visible', False):
                    try:
                        max_lines = 20
                        if len(LOG_BUFFER) > max_lines:
                            logs_text = "\n".join(list(LOG_BUFFER)[-max_lines:])
                        else:
                            logs_text = "\n".join(LOG_BUFFER)
                        self.logs_panel.update(logs_text)
                    except Exception:
                        pass
            except Exception:
                logging.exception('[TermoLoad] failed to flush LOG_BUFFER into logs_panel')
            try:
                no_dl = self.query_one("#no_downloads", Static)
                if len(self.downloads) == 0:
                    no_dl.visible = True
                    no_dl.display = True
                    try:
                        self.downloads_table.visible = False
                        self.downloads_table.display = False
                        self.downloads_toolbar.visible = False
                        self.downloads_toolbar.display = False
                    except Exception:
                        pass
                else:
                    no_dl.visible = False
                    no_dl.display = False
                    try:
                        self.downloads_table.visible = True
                        self.downloads_table.display = True
                        self.downloads_toolbar.visible = True
                        self.downloads_toolbar.display = True
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self.maybe_trigger_shutdown()
            except Exception:
                logging.exception("[TermoLoad] maybe_trigger_shutdown call failed")
            try:
                self._throttled_save_state()
            except Exception:
                pass
            try:
                sel = self._get_selected_download()
                if sel is not None:
                    txt = self._explain_status(sel.get("status", ""))
                    self.status_info.update(txt)
                    if sel.get("status") == "Completed":
                        filepath = self._resolve_download_path(sel)
                        if filepath and filepath.exists():
                            folder_name = filepath.parent.name
                            txt = f"✅ {txt} | 📁 Location: .../{folder_name}/"
                    self.status_info.update(txt)
                else:
                    self.status_info.update(txt)
           
            except Exception:
                pass
            try:
                if getattr(self.help_panel, 'visible', False):
                    self.help_panel.update(self._build_help_text())
            except Exception:
                pass
        except Exception:
            logging.exception("[TermoLoad] sync_table_from_downloads failed")

    def on_button_pressed(self, event) -> None:
        
        if event.button.id == "btn_add":
            self.push_screen(AddDownloadModal())
            return
        if event.button.id == "btn_minimize":
            self.minimize_to_tray()
            return
        if event.button.id == "btn_clear_history":
            try:
                self.history.clear_history()
                self.populate_history_table()
                self.notify("History cleared successfully !",severity="information")
            except Exception:
                self.notify("Failed to clear history.",severity="error")
            return
        if event.button.id == "btn_export_csv":
            try:
                self.export_history_csv()
            except Exception:
                self.notify("Failed to export history.",severity="error")
            return
        if event.button.id == "btn_pause_sel":
            self._pause_selected()
            return
        if event.button.id == "btn_resume_sel":
            self._resume_selected()
            return
        if event.button.id == "btn_pause_all":
            self._pause_all()
            return
        if event.button.id == "button_remove_list":
            self._remove_selected_from_list()
            return
        if event.button.id == "btn_delete_and_remove":
            # Show confirmation modal before deleting
            try:
                d = self._get_selected_download()
                if not d:
                    self.notify("No download selected to delete.", severity="warning")
                    return
                download_name = d.get("name", "Unknown")
                self.push_screen(ConfirmDeleteModal(download_name), self._on_delete_confirmed)
            except Exception as e:
                logging.exception(f"[TermoLoad] Error showing delete confirmation: {e}")
            return
        if event.button.id == "btn_resume_all":
            self._resume_all()
            return

        if event.button.id == "settings_browse":
            # Run dialog in background to prevent hanging in EXE
            async def browse_settings_folder():
                try:
                    folder = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: TkinterDialogHelper.ask_directory(title="Select Default Download Folder")
                    )
                    if folder:
                        try:
                            folder_input = self.query_one("#settings_download_folder", Input)
                            folder_input.value = folder
                        except Exception as e:
                            logging.exception(f"[TermoLoad] Error setting folder input: {e}")
                except Exception as e:
                    logging.exception(f"[TermoLoad] Error in settings browse: {e}")
            
            asyncio.create_task(browse_settings_folder())
            return

        if event.button.id == "settings_save":
            try:
                folder_input = self.query_one("#settings_download_folder", Input)
                concurrent_input = self.query_one("#settings_concurrent", Input)
                speed_input = self.query_one("#settings_speed", Input)
                shutdown_checkbox = self.query_one("#settings_shutdown", Checkbox)
                sound_complete_checkbox = self.query_one("#settings_sound_complete", Checkbox)
                sound_error_checkbox = self.query_one("#settings_sound_error", Checkbox)
                
                self.settings["download_folder"] = folder_input.value.strip() or str(Path.home() / "Downloads")
                try:
                    self.settings["concurrent"] = int(concurrent_input.value.strip() or 3)
                except Exception:
                    self.settings["concurrent"] = 3
                try:
                    self.settings["max_speed_kb"] = int(speed_input.value.strip() or 0)
                except Exception:
                    self.settings["max_speed_kb"] = 0
                
                self.settings["shutdown_on_complete"] = shutdown_checkbox.value
                self.settings["sound_on_complete"] = sound_complete_checkbox.value
                self.settings["sound_on_error"] = sound_error_checkbox.value
                self.save_settings()

            except Exception:
                logging.exception("[TermoLoad] failed to save settings from panel")

        if event.button.id == "settings_cancel":
            try:
                self.load_settings()
            except Exception:
                pass

        if event.button.id in ("btn_downloads", "btn_history", "btn_stats", "btn_settings", "btn_logs", "btn_help"):

            self.downloads_table.visible = False
            self.downloads_table.display = False
            self.downloads_toolbar.visible = False
            self.downloads_toolbar.display = False
            self.no_downloads.visible = False
            self.no_downloads.display = False
            self.status_info.visible = False
            self.status_info.display = False
            self.settings_panel.visible = False
            self.settings_panel.display = False
            self.logs_panel.visible = False
            self.logs_panel.display = False
            self.help_panel.visible = False
            self.help_panel.display = False
            self.history_panel.visible = False
            self.history_panel.display = False
            self.stats_panel.visible = False
            self.stats_panel.display = False

        if event.button.id == "btn_downloads":
            try:
                if len(self.downloads) > 0:
                    self.downloads_table.visible = True
                    self.downloads_table.display = True
                    self.downloads_toolbar.visible = True
                    self.downloads_toolbar.display = True
                    self.status_info.visible = True
                    self.status_info.display = True
                    self.no_downloads.visible = False
                    self.no_downloads.display = False
                else:
                    self.no_downloads.visible = True
                    self.no_downloads.display = True
                    self.downloads_table.visible = False
                    self.downloads_table.display = False
                    self.downloads_toolbar.visible = False
                    self.downloads_toolbar.display = False
                    self.status_info.visible = False
                    self.status_info.display = False
                try:
                    self.downloads_table.focus()
                except Exception:
                    pass
            except Exception:
                pass
            try:
                self.call_later(lambda: asyncio.create_task(self._deferred_scroll_to_top()))
            except Exception:
                try:
                    self.scroll_downloads_to_top()
                except Exception:
                    pass
        elif event.button.id == "btn_history":
            try:
                self.history_panel.visible = True
                self.history_panel.display = True
                self.populate_history_table()
            except Exception:
                pass
        elif event.button.id == "btn_stats":
            try:
                self.stats_panel.visible = True
                self.stats_panel.display = True
                stats_text = self.build_stats_display()
                self.stats_content.update(stats_text)
            except Exception:
                pass
        elif event.button.id == "btn_settings":
            try:
                self.settings_panel.visible = True
                self.settings_panel.display = True
            except Exception:
                pass
        elif event.button.id == "btn_logs":
            try:
                self.logs_panel.visible = True
                self.logs_panel.display = True
                try:
                    self.logs_panel.update("Loading logs...")
                except Exception:
                    pass
                try:
                    asyncio.create_task(self._update_logs_panel())
                except Exception:
                    pass
            except Exception:
                pass
        elif event.button.id == "btn_help":
            try:
                self.help_panel.visible = True
                self.help_panel.display = True
                try:
                    # Use the safe setter which handles ScrollView vs Static fallback
                    self._set_help_text()
                except Exception:
                    try:
                        # Last resort: direct update
                        self.help_panel.update(self._build_help_text())
                    except Exception:
                        pass
                try:
                    self.status_info.update("")
                except Exception:
                    pass
                try:
                    # Try to give keyboard focus to the help panel so keys scroll it
                    if hasattr(self, "set_focus"):
                        # schedule for later to ensure widget is mounted
                        try:
                            self.call_later(lambda: self.set_focus(self.help_panel))
                        except Exception:
                            # fallback to direct call
                            try:
                                self.set_focus(self.help_panel)
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception:
                pass

        self.refresh()
    
    def _export_history_csv(self):
        """Export history with async dialog to prevent EXE hanging."""
        async def do_export():
            try:
                import csv
                
                filepath = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: TkinterDialogHelper.ask_save_filename(
                        title="Export History as CSV",
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                    )
                )
                
                if not filepath:
                    return
                
                # Ensure .csv extension
                if not filepath.lower().endswith('.csv'):
                    filepath += '.csv'
                    
                with open(filepath, "w", newline='', encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Date", "Name", "Type", "Size (Bytes)", "Status", "URL", "Error"])
                    for entry in self.history.history:
                        writer.writerow([
                            entry.get("date", ""),
                            entry.get("name", ""),
                            entry.get("type", ""),
                            entry.get("size", 0),
                            entry.get("status", ""),
                            entry.get("url", ""),
                            entry.get("error", "")
                        ])
                self.notify(f"History exported successfully", severity="information", timeout=5)
                logging.info(f"[TermoLoad] History exported to {filepath}")
            except Exception:
                logging.exception("[TermoLoad] failed to export history to CSV")
                self.notify("Failed to export history", severity="error")
        
        asyncio.create_task(do_export())
        
    def _get_selected_download(self) -> Optional[Dict[str, Any]]:
        try:
            dt = self.downloads_table
            if hasattr(dt, "cursor_row") and dt.cursor_row is not None:
                idx = int(dt.cursor_row)
            elif hasattr(dt, "cursor_coordinate") and dt.cursor_coordinate is not None:
                idx = int(getattr(dt.cursor_coordinate, "row", 0))
            else:
                return None
            if 0 <= idx < len(self.downloads):
                return self.downloads[idx]
            return None
        except Exception:
            return None

    def _build_help_text(self) -> str:
        lines = []
        lines.append("TermoLoad — Help / Reference\n")
        lines.append("Controls\n--------")
        lines.append("a  Add Download")
        lines.append("q  Quit")
        lines.append("m  Minimize to Tray")
        lines.append("o  Open Folder (for completed downloads)")
        lines.append("Arrow keys select rows on Downloads tab")
        lines.append("")
        lines.append("Open Folder Feature\n-------------------")
        lines.append("When you select a completed download and press 'o':")
        lines.append("- Windows: Opens Explorer with the file highlighted")
        lines.append("- macOS: Opens Finder with the file revealed")
        lines.append("- Linux: Opens the folder in your default file manager")
        lines.append("This works individually for each download, regardless of where it was saved.")
        lines.append("")
        lines.append("Magnet Links & Torrents\n-----------------------")
        if LIBTORRENT_AVAILABLE:
            lines.append("✓ Full torrent support via libtorrent")
        else:
            lines.append("⚠ Torrent support unavailable - libtorrent not loaded")
            lines.append("  To enable: Install Microsoft Visual C++ Redistributable")
            lines.append("  Download: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        lines.append("- Supports .torrent files, magnet links, and torrent URLs")
        lines.append("- Names are extracted from magnet links (dn parameter)")
        lines.append("- Shows real-time peer/seed count and download speed")
        lines.append("- DHT, PEX, and tracker support enabled")
        lines.append("- Pause/resume works for torrents")
        lines.append("")
        lines.append("Supported Download Types\n------------------------")
        lines.append("✓ HTTP/HTTPS direct downloads (with resume support)")
        lines.append("✓ YouTube videos (requires yt-dlp)")
        lines.append("✓ Torrents (magnet links, .torrent files)")
        lines.append("")
        lines.append("Peers/Seeds Column\n------------------")
        lines.append("For torrent downloads, shows peer and seed count:")
        lines.append("- Format: peers↓/seeds↑ (e.g., '5↓/12↑' means 5 peers, 12 seeds)")
        lines.append("- 'Connecting...' - Searching for peers")
        lines.append("- 'Waiting...' - Torrent queued but not started")
        lines.append("- '--' - Not a torrent (URL/Video download)")
        lines.append("")
        lines.append("Common statuses\n----------------")
        lines.append("Downloading  Transfer in progress\nPaused       Task paused or canceled\nQueued       Waiting to start\nCompleted    Finished successfully\nProcessing   Video post-processing (yt-dlp/ffmpeg)")
        lines.append("")
        lines.append("Notification Sounds\n-------------------")
        lines.append("TermoLoad can play sounds when downloads complete or encounter errors.")
        lines.append("Enable/disable in Settings:")
        lines.append("- Completion sound: Pleasant ascending beep when download finishes")
        lines.append("- Error sound: Lower descending beep when download fails")
        lines.append("Both are enabled by default. Sounds play in the background.")
        lines.append("")
        try:
            errs = self._collect_current_errors()
        except Exception:
            errs = []
        lines.append("Recent errors (this session)\n----------------------------")
        if not errs:
            lines.append("No errors seen yet. If something fails, they will appear here.")
        else:
            grouped: Dict[str, List[str]] = {}
            for eid, name, err_text, hint in errs:
                key = f"{err_text}"
                label = f"[ID {eid}] {name}"
                grouped.setdefault(key, []).append(label)
            for err_text, labels in grouped.items():
                try:
                    hint = self._explain_status(err_text)
                    if hint and hint != err_text:
                        lines.append(f"- {err_text} — {hint.split(' — ', 1)[-1]}")
                    else:
                        lines.append(f"- {err_text}")
                except Exception:
                    lines.append(f"- {err_text}")
                try:
                    lines.append(f"    Affected: {', '.join(labels)}")
                except Exception:
                    pass
        lines.append("")
        lines.append("Major HTTP error codes\n-----------------------")
        codes = [
            ("200 OK", "Download started successfully"),
            ("206 Partial Content", "Server supports resume via HTTP Range (good)"),
            ("301/302/307/308 Redirect", "URL moved; TermoLoad follows automatically"),
            ("400 Bad Request", "Server rejected the request; check the URL"),
            ("401 Unauthorized", "Authentication required; the URL needs credentials"),
            ("403 Forbidden", "Access denied; you may not have permission"),
            ("404 Not Found", "The file or page doesn’t exist"),
            ("405 Method Not Allowed", "Server blocked the HTTP method"),
            ("408 Request Timeout", "Connection too slow or interrupted; try again"),
            ("409 Conflict", "Resource conflict; try later"),
            ("410 Gone", "The resource was removed permanently"),
            ("413 Payload Too Large", "Server refuses due to size or limits"),
            ("414 URI Too Long", "The link is too long for the server"),
            ("415 Unsupported Media Type", "Server rejected the content type"),
            ("416 Range Not Satisfiable", "Resume offset invalid; TermoLoad deletes the partial and restarts"),
            ("429 Too Many Requests", "You are rate-limited; wait and retry"),
            ("451 Unavailable For Legal Reasons", "Blocked by region/legal restrictions"),
            ("500 Internal Server Error", "Server error; retry later"),
            ("501 Not Implemented", "Server doesn’t support the request"),
            ("502 Bad Gateway", "Upstream server error"),
            ("503 Service Unavailable", "Server overloaded or down; retry later"),
            ("504 Gateway Timeout", "Upstream timeout; retry later"),
        ]
        for code, desc in codes:
            lines.append(f"{code:<24} {desc}")
        lines.append("")
        lines.append("Video errors (yt-dlp)\n----------------------")
        lines.append("- Error: yt-dlp not installed  → pip install yt-dlp\n- Merge/Processing issues       → install ffmpeg and ensure it’s in PATH\n- Some sites need cookies/login → not yet supported via UI; future work")
        lines.append("")
        lines.append("Where to look\n--------------")
        lines.append(f"- Logs tab shows the last 20 lines\n- Full log file: {LOG_FILE_PATH}\n- Download state is saved per-user: ~/downloads_state.json")
        return "\n".join(lines)

    def _set_help_text(self) -> None:
        txt = self._build_help_text()
        if ScrollView is not None and isinstance(self.help_panel, ScrollView):
            try:
                self.help_panel.update(txt)
            except Exception:
                pass
        else:
            # Fallback to Static: store lines and render a page
            self._help_text_lines = txt.split("\n")
            self._help_scroll = 0
            # compute a reasonable lines_per_page based on available panel height
            lines_per_page = 25
            try:
                # If the help panel has a size attribute, try to use its height
                h = None
                if hasattr(self.help_panel, "size"):
                    sz = getattr(self.help_panel, "size")
                    # size may be a tuple (width, height) or an object with .height
                    if isinstance(sz, tuple) and len(sz) >= 2:
                        h = sz[1]
                    else:
                        h = getattr(sz, "height", None)
                # fallback to app size
                if h is None and hasattr(self, "size"):
                    asz = getattr(self, "size")
                    if isinstance(asz, tuple) and len(asz) >= 2:
                        h = asz[1]
                    else:
                        h = getattr(asz, "height", None)
                if h is not None and isinstance(h, int) and h > 5:
                    # reserve a few rows for borders/headers
                    lines_per_page = max(5, h - 6)
            except Exception:
                pass
            self._render_help_page(lines_per_page=lines_per_page)

    def _render_help_page(self, lines_per_page: int = 25) -> None:
        try:
            if not self._help_text_lines:
                return
            start = self._help_scroll
            end = start + lines_per_page
            page = "\n".join(self._help_text_lines[start:end])
            try:
                self.help_panel.update(page)
            except Exception:
                pass
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key events for Static help scrolling fallback."""
        try:
            if getattr(self, 'help_panel', None) is None:
                return
            if ScrollView is not None:
                return  # ScrollView handles keys itself
            # Only respond when help panel visible
            if not getattr(self.help_panel, 'visible', False):
                return
            key = getattr(event, 'key', None) or getattr(event, 'key', '')
            if not key:
                return
            # Basic navigation
            # helper to compute current lines per page similar to _set_help_text
            def _current_lines_per_page():
                lines_per_page = 25
                try:
                    h = None
                    if hasattr(self.help_panel, "size"):
                        sz = getattr(self.help_panel, "size")
                        if isinstance(sz, tuple) and len(sz) >= 2:
                            h = sz[1]
                        else:
                            h = getattr(sz, "height", None)
                    if h is None and hasattr(self, "size"):
                        asz = getattr(self, "size")
                        if isinstance(asz, tuple) and len(asz) >= 2:
                            h = asz[1]
                        else:
                            h = getattr(asz, "height", None)
                    if h is not None and isinstance(h, int) and h > 5:
                        lines_per_page = max(5, h - 6)
                except Exception:
                    pass
                return lines_per_page

            if key.lower() in ('down', 'j'):
                self._help_scroll = min(len(self._help_text_lines)-1, self._help_scroll + 1)
                self._render_help_page(lines_per_page=_current_lines_per_page())
                event.stop()
            elif key.lower() in ('up', 'k'):
                self._help_scroll = max(0, self._help_scroll - 1)
                self._render_help_page(lines_per_page=_current_lines_per_page())
                event.stop()
            elif key.lower() in ('pageup',):
                lpp = _current_lines_per_page()
                self._help_scroll = max(0, self._help_scroll - lpp)
                self._render_help_page(lines_per_page=lpp)
                event.stop()
            elif key.lower() in ('pagedown',):
                lpp = _current_lines_per_page()
                self._help_scroll = min(max(0, len(self._help_text_lines)-1), self._help_scroll + lpp)
                self._render_help_page(lines_per_page=lpp)
                event.stop()
            elif key.lower() in ('home',):
                self._help_scroll = 0
                self._render_help_page(lines_per_page=_current_lines_per_page())
                event.stop()
            elif key.lower() in ('end',):
                # move to last page start
                lpp = _current_lines_per_page()
                self._help_scroll = max(0, len(self._help_text_lines)-lpp)
                self._render_help_page(lines_per_page=lpp)
                event.stop()
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event) -> None:
        """Track when user highlights a row to prevent table updates during interaction."""
        try:
            self._user_interacting = True
            self._last_interaction_time = time.time()
        except Exception:
            pass
    
    def on_data_table_row_selected(self, event) -> None:
        """Track when user selects a row."""
        try:
            self._user_interacting = True
            self._last_interaction_time = time.time()
        except Exception:
            pass
    
    def on_data_table_cell_highlighted(self, event) -> None:
        """Track when user highlights a cell."""
        try:
            self._user_interacting = True
            self._last_interaction_time = time.time()
        except Exception:
            pass
    
    def on_mouse_down(self, event) -> None:
        """Track mouse down events on the table."""
        try:
            # Check if the event is on the downloads table
            if hasattr(event, 'widget') and event.widget == self.downloads_table:
                self._user_interacting = True
                self._last_interaction_time = time.time()
        except Exception:
            pass
    
    def on_mouse_up(self, event) -> None:
        """Reset interaction flag after mouse up."""
        try:
            if hasattr(event, 'widget') and event.widget == self.downloads_table:
                # Small delay before allowing updates again
                self._last_interaction_time = time.time()
        except Exception:
            pass

    def _collect_current_errors(self) -> List[tuple]:
        out: List[tuple] = []
        try:
            for d in getattr(self, 'downloads', []) or []:
                st = str(d.get("status", "")).strip()
                if st.startswith("Error:"):
                    did = d.get("id")
                    nm = d.get("name") or d.get("url") or f"download_{did}"
                    hint = self._explain_status(st)
                    out.append((did, nm, st, hint))
        except Exception:
            pass
        return out

    def _explain_status(self, status: str) -> str:
        if not status:
            return ""
        s = status.strip()
        if s.startswith("Error:"):
            code = s.split(":", 1)[-1].strip()
            mapping = {
                "400": "Bad Request – The server rejected the request. Check the URL.",
                "401": "Unauthorized – The URL requires authentication.",
                "403": "Forbidden – You don't have permission.",
                "404": "Not Found – The file or page doesn't exist.",
                "405": "Method Not Allowed – Server blocked the HTTP method.",
                "408": "Request Timeout – Connection was too slow or interrupted.",
                "409": "Conflict – Resource state conflict; retry later.",
                "410": "Gone – Resource removed permanently.",
                "413": "Payload Too Large – File too big or server limits exceeded.",
                "414": "URI Too Long – Link too long for the server.",
                "415": "Unsupported Media Type – Server rejected the content type.",
                "416": "Range Not Satisfiable – Resume offset invalid; TermoLoad restarts cleanly.",
                "429": "Too Many Requests – You're rate-limited; wait and retry.",
                "451": "Unavailable For Legal Reasons – Blocked by region/legal restrictions.",
                "500": "Internal Server Error – Server failure; retry later.",
                "501": "Not Implemented – Server doesn't support the request.",
                "502": "Bad Gateway – Upstream server error.",
                "503": "Service Unavailable – Server overloaded or down; retry later.",
                "504": "Gateway Timeout – Upstream timeout; retry later.",
            }
            tips = mapping.get(code, "Unknown error – check logs for details.")
            return f"{s} — {tips}"
        elif s == "Processing":
            return "Processing – Finishing up video merge (yt-dlp/ffmpeg)."
        elif s == "Paused":
            return "Paused – Use 'Resume Selected' to continue."
        elif s == "Queued":
            return "Queued – Waiting for a free slot to start."
        elif s == "Downloading":
            return "Downloading – Transfer in progress."
        elif s == "Completed":
            return "Completed – File is ready. Press 'o' to open folder"
        return s

    def _resolve_download_path(self, d: dict) -> Optional[Path]:
        """Resolve the final file path for a download entry.
        Uses stored filepath when available; otherwise derives from path+name.
        """
        try:
            fp = d.get("filepath")
            if fp:
                return Path(fp)
            base_dir = d.get("path") or self.settings.get("download_folder", str(Path.home() / "Downloads"))
            name = d.get("name")
            if base_dir and name:
                return Path(base_dir) / name
            return None
        except Exception:
            return None

    def _delete_download_files(self, d: dict, delete_partials: bool = True) -> int:
        deleted = 0
        try:
            main_path = self._resolve_download_path(d)
            if main_path and main_path.exists():
                try:
                    # If it's a directory (e.g., torrent save folder), remove recursively
                    if main_path.is_dir():
                        shutil.rmtree(main_path)
                        deleted += 1
                    else:
                        main_path.unlink()
                        deleted += 1
                except Exception:
                    logging.exception(f"[TermoLoad] failed to delete file/directory: {main_path}")
            if delete_partials and main_path:
                candidates = [
                    Path(str(main_path) + ".part"),
                    Path(str(main_path) + ".tmp"),
                    main_path.with_suffix(main_path.suffix + ".part"),
                    main_path.with_suffix(main_path.suffix + ".ytdl"),
                    main_path.with_suffix(main_path.suffix + ".temp"),
                ]
                for p in candidates:
                    try:
                        if p.exists():
                            p.unlink()
                            deleted += 1
                    except Exception:
                        pass
            # For torrents, also attempt to remove the containing folder if empty
            if d.get("type") == "Torrent" and main_path:
                parent = main_path.parent
                # Only remove the parent directory if it's inside the download folder and is empty
                download_folder = Path(d.get("path") or self.settings.get("download_folder", "downloads"))
                try:
                    if parent != download_folder and str(parent).startswith(str(download_folder)):
                        # Attempt remove if empty
                        if parent.exists() and not any(parent.iterdir()):
                            parent.rmdir()
                except Exception:
                    pass
        except Exception:
            logging.exception("[TermoLoad] _delete_download_files unexpected error")
        return deleted

    def _remove_download_entry(self, download_id: int) -> None:
        try:
            task = self.download_tasks.pop(download_id, None)
            if task and not task.done():
                try:
                    task.cancel()
                except Exception:
                    pass
            idx = None
            row_key = None
            for i, item in enumerate(self.downloads):
                if int(item.get("id")) == int(download_id):
                    idx = i
                    row_key = item.get("row_key")
                    break
            try:
                if row_key is not None:
                    self.downloads_table.remove_row(row_key)
            except Exception:
                pass
            if idx is not None:
                self.downloads.pop(idx)
            self.save_downloads_state()
        except Exception:
            logging.exception("[TermoLoad] _remove_download_entry failed")

    def _delete_selected_file(self, delete_partials: bool = True) -> None:
        d = self._get_selected_download()
        if not d:
            return
        self._delete_download_files(d, delete_partials=delete_partials)
        try:
            d.pop("filepath", None)
        except Exception:
            pass
        self.save_downloads_state()

    def _remove_selected_from_list(self) -> None:
        d = self._get_selected_download()
        if not d:
            return
        try:
            self._remove_download_entry(int(d.get("id")))
        except Exception:
            logging.exception("[TermoLoad] _remove_selected_from_list failed")

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        """Callback when user responds to delete confirmation modal."""
        if confirmed:
            # User confirmed deletion, proceed with delete
            asyncio.create_task(self._delete_selected_file_async(delete_partials=True, remove_from_list=True))
            self.notify("Deleting files and removing from list...", severity="information")
        else:
            # User cancelled
            self.notify("Delete cancelled.", severity="information")

    def _handle_torrent_file_selection(self, result: Optional[dict], download_id: int, custom_path: str, url: str, name: str, d_type: str) -> None:
        """Handle the result from TorrentFileSelectModal and create download entry."""
        try:
            if not result:
                # User cancelled - clean up temp handle
                temp_key = f"temp_{download_id}"
                handle = self.downloader.torrent_handles.pop(temp_key, None)
                if handle and self.downloader.torrent_session:
                    try:
                        self.downloader.torrent_session.remove_torrent(handle)
                    except:
                        pass
                
                self.notify("Torrent download cancelled", severity="information")
                return
            
            selected_files = result.get("selected_files", [])
            torrent_info = result.get("torrent_info", {})
            
            logging.info(f"[TermoLoad] User selected {len(selected_files)} files from torrent")
            
            # Update name from torrent info
            torrent_name = torrent_info.get("name", name)
            
            # NOW create the download entry
            new_entry = {
                "id": download_id,
                "type": d_type,
                "name": torrent_name,
                "url": url,
                "path": custom_path,
                "progress": 0.0,
                "speed": "0 B/s",
                "status": "Queued",
                "eta": "--",
                "peers": 0,
                "seeds": 0
            }
            
            # Add to table
            try:
                row_key = self.downloads_table.add_row(
                    str(new_entry["id"]),
                    new_entry["type"],
                    new_entry["name"],
                    "0.00%",
                    "0 B/s",
                    "Waiting...",
                    new_entry["status"],
                    "--"
                )
                new_entry["row_key"] = row_key
            except Exception:
                logging.exception("[TermoLoad] Failed to add torrent row to table")
                return
            
            # Add to downloads list
            self.downloads.append(new_entry)
            
            # Save state
            try:
                self.save_downloads_state()
            except Exception:
                pass
            
            # Show UI elements
            try:
                self.downloads_table.visible = True
                self.downloads_table.display = True
                self.downloads_toolbar.visible = True
                self.downloads_toolbar.display = True
                self.status_info.visible = True
                self.status_info.display = True
                self.no_downloads.visible = False
                self.no_downloads.display = False
                self.settings_panel.visible = False
                self.settings_panel.display = False
                self.logs_panel.visible = False
                self.logs_panel.display = False
                self.help_panel.visible = False
                self.help_panel.display = False
            except Exception:
                pass
            
            # Scroll to top
            try:
                self.call_later(lambda: asyncio.create_task(self._deferred_scroll_to_top()))
            except Exception:
                try:
                    self.scroll_downloads_to_top()
                except Exception:
                    pass
            
            # Create the download task with file selection
            task = asyncio.create_task(
                self.downloader.download_torrent(url, download_id, custom_path, selected_files)
            )
            self.download_tasks[download_id] = task
            
            self.notify(f"Starting download: {len(selected_files)} of {torrent_info.get('num_files', 0)} files", severity="information")
            logging.info(f"[TermoLoad] Created asyncio task for selective torrent download {download_id}")
            
        except Exception:
            logging.exception("[TermoLoad] _handle_torrent_file_selection failed")
            
        except Exception:
            logging.exception("[TermoLoad] _handle_torrent_file_selection failed")

    async def _delete_selected_file_async(self, delete_partials: bool = True, remove_from_list: bool = False) -> None:
        d = self._get_selected_download()
        if not d:
            return
        did = int(d.get("id"))
        try:
            task = self.download_tasks.get(did)
            if task and not task.done():
                # Cancel running asyncio task
                task.cancel()
                await asyncio.sleep(0)
        except Exception:
            pass
        # If it's a torrent, attempt to stop/remove the torrent handle so files can be deleted
        try:
            d_type = d.get("type")
            if d_type == "Torrent":
                try:
                    # Ask downloader to remove torrent handle
                    try:
                        self.downloader.remove_torrent(did)
                    except Exception:
                        pass
                    # also remove from downloader.torrent_handles if present
                    try:
                        self.downloader.torrent_handles.pop(did, None)
                    except Exception:
                        pass
                    # small delay to allow libtorrent to release file handles
                    await asyncio.sleep(0.2)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            d["status"] = "Paused"
        except Exception:
            pass
        self._delete_download_files(d, delete_partials=delete_partials)
        try:
            d.pop("filepath", None)
        except Exception:
            pass
        self.save_downloads_state()
        if remove_from_list:
            try:
                self._remove_download_entry(did)
            except Exception:
                pass

    def _pause_download(self, download_id: int) -> None:
        try:
            d = next((x for x in self.downloads if x.get("id") == download_id), None)
            if d and d.get("type") == "Torrent":
                self.downloader.pause_torrent(download_id)
            task = self.download_tasks.get(download_id)
            if task and not task.done():
                task.cancel()
                if d and d.get("status") == "Downloading":
                    try:
                        self.history.add_entry(d , "cancelled")
                    except Exception:
                        pass
            for d in self.downloads:
                if d.get("id") == download_id:
                    d["status"] = "Paused"
                    break
            self.save_downloads_state()
        except Exception:
            logging.exception("[TermoLoad] _pause_download failed")

    def _resume_download(self, download_id: int) -> None:
        try:
            d = next((x for x in self.downloads if x.get("id") == download_id), None)
            if not d:
                return
            t = self.download_tasks.get(download_id)
            if t and not t.done():
                return
            url = d.get("url")
            name = d.get("name")
            save_path = d.get("path") or "downloads"

            try:
                if d.get("status") == "Completed":
                    fp = d.get("filepath")
                    if fp:
                        try:
                            Path(fp).unlink(missing_ok=True)
                        except Exception:
                            pass
                    else:
                        try:
                            derived = Path(save_path) / (name or f"download_{download_id}")
                            derived.unlink(missing_ok=True)
                        except Exception:
                            pass
                    d["progress"] = 0.0
                    d["speed"] = "0 B/s"
                    d["eta"] = "--"
                    d["downloaded_bytes"] = 0
                    d["total_size"] = 0
                    d["filepath"] = ""
            except Exception:
                pass

            d["status"] = "Queued"
            if d.get("type") == "Torrent":
               logging.info(f"[TermoLoad] Starting Torrent Download :{name}")
               task = asyncio.create_task(self.downloader.download_torrent(url, download_id, save_path))
            elif d.get("type") == "Video":
                task = asyncio.create_task(self.downloader.download_with_ytdlp(url, download_id, save_path, None))
            else:
                task = asyncio.create_task(self.downloader.download_file(url, download_id, name, save_path))
            self.download_tasks[download_id] = task
            self.save_downloads_state()
        except Exception:
            logging.exception("[TermoLoad] _resume_download failed")

    def _pause_selected(self) -> None:
        d = self._get_selected_download()
        if d:
            self._pause_download(int(d.get("id")))

    def _resume_selected(self) -> None:
        d = self._get_selected_download()
        if d:
            self._resume_download(int(d.get("id")))

    def _pause_all(self) -> None:
        for d in list(self.downloads):
            self._pause_download(int(d.get("id")))

    def _resume_all(self) -> None:
        for d in list(self.downloads):
            self._resume_download(int(d.get("id")))

    def action_add_download(self) -> None:
        """Add a new download - opens modal dialog."""
        try:
            self.push_screen(AddDownloadModal())
        except Exception as e:
            logging.exception(f"[TermoLoad] Error opening add download modal: {e}")
            self.notify("Error opening download dialog", severity="error")
           
    
    async def on_screen_dismissed(self, event):
        """Handle modal screen dismissal with proper error handling."""
        try:
            logging.info(f"[TermoLoad] on_screen_dismissed CALLED: screen={type(event.screen)} result={event.result}")
            
            if isinstance(event.screen, AddDownloadModal):
                logging.info("[TermoLoad] on_screen_dismissed: AddDownloadModal detected")
                result = event.result
                logging.info(f"[TermoLoad] on_screen_dismissed: result={result}")
                
                if not result or not isinstance(result, dict):
                    logging.info("[TermoLoad] No result or invalid result type")
                    return
                
                url = result.get("url", "").strip()
                custom_path = result.get("path", "").strip()
                
                if not url:
                    self.notify("Invalid URL provided", severity="warning")
                    return
                    
                logging.info(f"[TermoLoad] on_screen_dismissed: url={url}, custom_path={custom_path}")
                
                # Use atomic counter for ID generation
                new_id = len(self.downloads) + 1
                
                is_torrent = (
                    url.startswith("magnet:") or
                    url.lower().endswith(".torrent") or
                    (os.path.isfile(url) and url.lower().endswith(".torrent"))
                )
                
                logging.info(f"[TermoLoad] is_torrent={is_torrent} for url={url}")
                
                if is_torrent:
                    d_type = "Torrent"
                    if os.path.isfile(url):
                        name = os.path.basename(url)
                    elif url.startswith("magnet:"):
                        extracted_name = RealDownloader.extract_magnet_name(url)
                        if extracted_name:
                            name = extracted_name
                        else:
                            name = f"magnet_torrent_{new_id}"
                    else:
                        try:
                            parsed_name = os.path.basename(urlparse(url).path)
                            name = parsed_name if parsed_name else f"torrent_{new_id}"
                        except Exception:
                            name = f"torrent_{new_id}"
                else:
                    d_type = "URL"
                    try:
                        if RealDownloader.is_video_url(url):
                            d_type = "Video"
                    except Exception:
                        pass

                    if url.startswith(("http://", "https://")):
                        name = os.path.basename(urlparse(url).path) or f"download_{new_id}"
                    else:
                        name = url.split("/")[-1] or f"download_{new_id}"

                # For torrents, handle file selection FIRST before creating entry
                if d_type == "Torrent":
                    # Check if libtorrent is available
                    if not LIBTORRENT_AVAILABLE:
                        self.notify(
                            "Torrent downloads unavailable. Install Visual C++ Redistributables.",
                            severity="error",
                            timeout=5
                        )
                        logging.error("[TermoLoad] Cannot add torrent - libtorrent not available")
                        return
                    
                    logging.info(f"[TermoLoad] Fetching torrent info for file selection...")
                    self.notify("Fetching torrent information...", severity="information")
                    
                    try:
                        # Fetch torrent info first
                        torrent_info = await self.downloader.get_torrent_info(url, new_id)
                        
                        logging.info(f"[TermoLoad] Torrent info received: {torrent_info is not None}")
                        if torrent_info:
                            logging.info(f"[TermoLoad] Torrent has {len(torrent_info.get('files', []))} files")
                        
                        if not torrent_info:
                            self.notify("Failed to fetch torrent information", severity="error")
                            logging.error("[TermoLoad] get_torrent_info returned None")
                            return
                        
                        # Show file selection modal
                        logging.info(f"[TermoLoad] About to show TorrentFileSelectModal...")
                        def handle_file_selection(result):
                            logging.info(f"[TermoLoad] File selection callback triggered with result: {result is not None}")
                            self._handle_torrent_file_selection(result, new_id, custom_path, url, name, d_type)
                        
                        self.push_screen(TorrentFileSelectModal(torrent_info), handle_file_selection)
                        logging.info(f"[TermoLoad] TorrentFileSelectModal pushed to screen")
                        
                    except Exception as ex:
                        logging.exception(f"[TermoLoad] Failed to fetch torrent info: {ex}")
                        self.notify("Error fetching torrent files", severity="error")
                    
                    return  # Don't proceed with normal download flow
                
                # For non-torrent downloads, create entry normally
                new_entry = {
                    "id": new_id,
                    "type": d_type,
                    "name": name,
                    "url": url,
                    "path": custom_path,
                    "progress": 0.0,
                    "speed": "0 B/s",
                    "status": "Queued",
                    "eta": "--",
                    "peers": 0,
                    "seeds": 0
                }
                
                logging.info(f"[TermoLoad] on_screen_dismissed: new_entry={new_entry}")
                peers_seeds = "Waiting..." if d_type == "Torrent" else "--"
                
                try:
                    row_key = self.downloads_table.add_row(
                        str(new_entry["id"]),
                        new_entry["type"],
                        new_entry["name"],
                        "0.00%",
                        "0 B/s",
                        peers_seeds,
                        new_entry["status"],
                        "--"
                    )
                except Exception:
                    row_key = len(self.downloads)
                    try:
                        self.downloads_table.add_row(
                            str(new_entry["id"]),
                            new_entry["type"],
                            new_entry["name"],
                            "0.00%",
                            "0 B/s",
                            peers_seeds,
                            new_entry["status"],
                            "--"
                        )
                    except Exception:
                        logging.exception("[TermoLoad] on_screen_dismissed: failed to add row to table")
                new_entry["row_key"] = row_key
                self.downloads.append(new_entry)
                try:
                    self.save_downloads_state()
                except Exception:
                    pass
                try:
                    self.call_later(lambda: asyncio.create_task(self._deferred_scroll_to_top()))
                except Exception:
                    try:
                        self.scroll_downloads_to_top()
                    except Exception:
                        pass
                try:
                    self.downloads_table.visible = True
                    self.downloads_table.display = True
                    self.downloads_toolbar.visible = True
                    self.downloads_toolbar.display = True
                    self.status_info.visible = True
                    self.status_info.display = True
                    self.no_downloads.visible = False
                    self.no_downloads.display = False
                    self.settings_panel.visible = False
                    self.settings_panel.display = False
                    self.logs_panel.visible = False
                    self.logs_panel.display = False
                    self.help_panel.visible = False
                    self.help_panel.display = False
                except Exception:
                    pass
                
                # Start the download task based on type (non-torrents only)
                if d_type == "URL":
                    logging.info(f"[TermoLoad] Queuing download {new_id} -> {url} -> {custom_path}")
                    try:
                        task = asyncio.create_task(
                            self.downloader.download_file(url, new_id, name, custom_path)
                        )
                        self.download_tasks[new_id] = task
                        logging.info(f"[TermoLoad] Created asyncio task for download {new_id}")
                    except Exception as ex:
                        logging.exception(f"[TermoLoad] Failed to create task: {ex}")
                elif d_type == "Video":
                    logging.info(f"[TermoLoad] Queuing yt-dlp download {new_id} -> {url} -> {custom_path}")
                    try:
                        for item in self.downloads:
                                if item.get("id") == new_id:
                                    item["name"] = item.get("name") or "(resolving title...)"
                                    break
                        task = asyncio.create_task(
                            self.downloader.download_with_ytdlp(url, new_id, custom_path, None)
                        )
                        self.download_tasks[new_id] = task
                        logging.info(f"[TermoLoad] Created asyncio task for yt-dlp download {new_id}")
                    except Exception as ex:
                            logging.exception(f"[TermoLoad] Failed to create yt-dlp task: {ex}")
        
        except Exception as e:
            logging.exception(f"[TermoLoad] Error in on_screen_dismissed: {e}")
            self.notify("Error processing download request", severity="error")

    
    def scroll_downloads_to_top(self) -> None:
        try:
            if hasattr(self, 'downloads_table'):
                dt = self.downloads_table
                if hasattr(dt, 'scroll_to_row'):
                    dt.scroll_to_row(0)
                elif hasattr(dt, 'action_scroll_home'):
                    dt.action_scroll_home()
                else:
                    dt.focus()
        except Exception:
            logging.exception('[TermoLoad] scroll_downloads_to_top failed')

    async def _deferred_scroll_to_top(self, retries: int = 4, delay: float = 0.05):
        try:
            for _ in range(retries):
                try:
                    self.scroll_downloads_to_top()
                    return
                except Exception:
                    await asyncio.sleep(delay)
            try:
                self.scroll_downloads_to_top()
            except Exception:
                pass
        except Exception:
            logging.exception('[TermoLoad] _deferred_scroll_to_top failed')

    def maybe_trigger_shutdown(self):
        try:
            if not self.settings.get("shutdown_on_complete", False):
                self._shutdown_triggered = False
                return
            if not self.downloads:
                return

            all_completed = all(d.get("status") == "Completed" for d in self.downloads)
            active = [d for d in self.downloads if d.get("status") in ("Downloading", "Queued")]
            if active:
                self._previous_had_active = True
                self._shutdown_triggered = False
                logging.info(f"[TermoLoad] maybe_trigger_shutdown: active downloads remain, not shutting down ({len(active)})")
                return
            if not self._previous_had_active:
                logging.debug("[TermoLoad] maybe_trigger_shutdown: all downloads completed but no earlier activity seen; skipping")
                return

            if self._shutdown_triggered:
                return

            if all_completed:
                logging.info("[TermoLoad] maybe_trigger_shutdown: All downloads completed, initiating shutdown")
                try:
                    if sys.platform.startswith("win"):
                        cmd = ["shutdown", "/s", "/t", "0"]
                    else:
                        cmd = ["shutdown", "-h", "now"]
                    subprocess.Popen(cmd, shell=False)
                    logging.info(f"[TermoLoad] maybe_trigger_shutdown: Shutdown command executed: {' '.join(cmd)}")
                except Exception:
                    logging.exception("[TermoLoad] maybe_trigger_shutdown: Failed to execute shutdown command")
                self._shutdown_triggered = True
        except Exception:
            logging.exception("[TermoLoad] maybe_trigger_shutdown unexpected error")
    
    
    def process_modal_result(self, result: dict):
        try:
            logging.info(f"[TermoLoad] process_modal_result called with: {result}")
            if not result or not isinstance(result, dict):
                logging.debug("[TermoLoad] process_modal_result: nothing to do (no result)")
                return

            url = result.get('url')
            custom_path = result.get('path')

            new_id = len(self.downloads) + 1
            is_torrent =(
                url.startswith("magnet:") or
                url.endswith(".torrent") or
                (os.path.isfile(url) and url.lower().endswith(".torrent"))
                    )
            if is_torrent:
                d_type = "Torrent"
                if os.path.isfile(url):
                    name = os.path.basename(url)
                else:
                    name = f"torrent_{new_id}"
            else:
                d_type = "URL"
            try:
                if RealDownloader.is_video_url(url):
                    d_type = "Video"
            except Exception:
                pass

            if url.startswith(("http://", "https://")):
                name = os.path.basename(urlparse(url).path) or f"download_{new_id}"
            else:
                name = url.split("/")[-1] or f"download_{new_id}"

            new_entry = {
                "id": new_id,
                "type": d_type,
                "name": name,
                "url": url,
                "path": custom_path,
                "progress": 0.0,
                "speed": "0 B/s",
                "status": "Queued" if d_type != "Torrent" else "Pending",
                "eta": "--"
            }

            logging.info(f"[TermoLoad] process_modal_result: appending new_entry {new_entry}")
            try:
                row_key = self.downloads_table.add_row(
                    str(new_entry["id"]),
                    new_entry["type"],
                    new_entry["name"],
                    "0.00%",
                    "0 B/s",
                    new_entry["status"],
                    "--"
                )
                new_entry["row_key"] = row_key
            except Exception:
                logging.exception("[TermoLoad] process_modal_result: failed to add row to table")
                new_entry["row_key"] = len(self.downloads)
            self.downloads.append(new_entry)
            try:
                self.save_downloads_state()
            except Exception:
                pass

            try:
                self.scroll_downloads_to_top()
            except Exception:
                pass
            try:
                self.downloads_table.visible = True
                self.downloads_table.display = True
                self.downloads_toolbar.visible = True
                self.downloads_toolbar.display = True
                self.status_info.visible = True
                self.status_info.display = True
                self.no_downloads.visible = False
                self.no_downloads.display = False
                self.settings_panel.visible = False
                self.settings_panel.display = False
                self.logs_panel.visible = False
                self.logs_panel.display = False
                self.help_panel.visible = False
                self.help_panel.display = False
            except Exception:
                pass
            if d_type == "Torrent":
                logging.info(f"[TermoLoad] Torrent detected: {url}")
                # Start torrent task immediately (auto-start)
                if not LIBTORRENT_AVAILABLE:
                    self.notify(
                        "Torrent downloads unavailable. Install Visual C++ Redistributables.",
                        severity="error",
                        timeout=5
                    )
                    logging.error("[TermoLoad] Cannot add torrent - libtorrent not available")
                else:
                    try:
                        # mark as queued and create asyncio task
                        for d in self.downloads:
                            if d.get("id") == new_id:
                                d["status"] = "Queued"
                                break
                        task = asyncio.create_task(
                            self.downloader.download_torrent(url, new_id, custom_path)
                        )
                        self.download_tasks[new_id] = task
                        logging.info(f"[TermoLoad] process_modal_result: Created asyncio task for torrent {new_id}")
                    except Exception as ex:
                        logging.exception(f"[TermoLoad] process_modal_result: Failed to create torrent task: {ex}")
            elif d_type == "URL":
                logging.info(f"[TermoLoad] process_modal_result: Queuing download {new_id} -> {url} -> {custom_path}")
                try:
                    task = asyncio.create_task(
                        self.downloader.download_file(url, new_id, name, custom_path)
                    )
                    self.download_tasks[new_id] = task
                    logging.info(f"[TermoLoad] process_modal_result: Created asyncio task for download {new_id}")
                except Exception as ex:
                    logging.exception(f"[TermoLoad] process_modal_result: Failed to create task: {ex}")
            
            elif d_type == "Video":
                logging.info(f"[TermoLoad] process_modal_result: Queuing yt-dlp download {new_id} -> {url} -> {custom_path}")
                try:
                    for item in self.downloads:
                        if item.get("id") == new_id:
                                item["name"] = item.get("name") or "(resolving title...)"
                                break
                    task = asyncio.create_task(
                        self.downloader.download_with_ytdlp(url, new_id, custom_path, None)
                    )
                    self.download_tasks[new_id] = task
                    logging.info(f"[TermoLoad] process_modal_result: Created asyncio task for yt-dlp download {new_id}")
                except Exception as ex:
                    logging.exception(f"[TermoLoad] process_modal_result: Failed to create yt-dlp task: {ex}")
        except Exception:
            logging.exception("[TermoLoad] process_modal_result: unexpected error")

    async def on_unmount(self) -> None:
        """Clean up resources when app is closing."""
        try:
            # Clean up tkinter resources
            TkinterDialogHelper.cleanup()
            
            for d in self.downloads:
                if d.get("status") in ("Downloading", "Queued"):
                    d["status"] = "Paused"
            self.save_downloads_state(force=True)
        except Exception as e:
            logging.exception(f"[TermoLoad] Error during unmount cleanup: {e}")

        # Cancel all download tasks
        for task in self.download_tasks.values():
            if not task.done():
                task.cancel()
        
        # Clean up torrent session
        try:
            if self.downloader.torrent_session:
                logging.info("[TermoLoad] Cleaning up torrent session...")
                
                # Pause all active torrents
                for download_id, handle in list(self.downloader.torrent_handles.items()):
                    try:
                        logging.info(f"[TermoLoad] Pausing torrent {download_id}")
                        handle.pause()
                        
                        try:
                            if handle.need_save_resume_data():
                                handle.save_resume_data()
                        except Exception:
                            pass
                    except Exception:
                        logging.exception(f"[TermoLoad] Failed to pause torrent {download_id}")
                
                await asyncio.sleep(0.5)
                
                # Pause the session
                try:
                    self.downloader.torrent_session.pause()
                    logging.info("[TermoLoad] Libtorrent session paused successfully")
                except Exception:
                    logging.exception("[TermoLoad] Failed to pause torrent session")
                
                # Clear handles
                self.downloader.torrent_handles.clear()
                
        except Exception:
            logging.exception("[TermoLoad] Failed to cleanup torrent session")
        
        # Close HTTP session
        await self.downloader.close_session()
        
        logging.info("[TermoLoad] App unmounted successfully")
    
    async def _update_logs_panel(self):
        try:
            if not hasattr(self, 'logs_panel') or not self.logs_panel:
                return
            lines = list(LOG_BUFFER)
            max_lines = 20
            start = max(0, len(lines) - max_lines)
            chunk_size = 200
            try:
                self.logs_panel.update("")
            except Exception:
                pass
            for i in range(start, len(lines), chunk_size):
                if not getattr(self.logs_panel, 'visible', False):
                    return
                chunk = lines[i:i+chunk_size]
                text = "\n".join(chunk)
                try:
                    existing = getattr(self.logs_panel, 'renderable', None) or ""
                    new_text = (existing + "\n" + text).lstrip("\n")
                    self.logs_panel.update(new_text)
                except Exception:
                    pass
                await asyncio.sleep(0)
        except Exception:
            logging.exception("[TermoLoad] _update_logs_panel failed")

    def _state_file(self) -> Path:
        return Path.home() / "downloads_state.json"

    def save_downloads_state(self, force: bool = False) -> None:
        try:
            data = {
                "downloads": [
                    {
                        "id": d.get("id"),
                        "type": d.get("type"),
                        "name": d.get("name"),
                        "url": d.get("url"),
                        "path": d.get("path"),
                        "progress": float(d.get("progress", 0.0)),
                        "speed": d.get("speed", "0 B/s"),
                        "status": d.get("status", "Queued"),
                        "eta": d.get("eta", "--"),
                        "downloaded_bytes": int(d.get("downloaded_bytes", 0) or 0),
                        "total_size": int(d.get("total_size", 0) or 0),
                        "filepath": d.get("filepath", ""),
                        "peers": d.get("peers", 0),
                        "seeds":d.get("seeds", 0)
                    }
                    for d in self.downloads
                ]
            }
            with self._state_file().open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            logging.exception("[TermoLoad] Failed to save downloads_state.json")

    def load_downloads_state(self) -> List[Dict[str, Any]]:
        path = self._state_file()
        if not path.exists():
            legacy = Path("downloads_state.json")
            if not legacy.exists():
                return []
            try:
                with legacy.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("downloads", [])
            except Exception:
                logging.exception("[TermoLoad] Failed to read legacy downloads_state.json")
                return []
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("downloads", [])
        except Exception:
            logging.exception("[TermoLoad] Failed to read downloads_state.json")
            return []

    def _throttled_save_state(self) -> None:
        now = time.time()
        last = getattr(self, "_last_state_save", 0)
        if now - last >= 2.0:
            self.save_downloads_state()
            self._last_state_save = now

    async def _resume_incomplete_downloads(self) -> None:
        try:
            await self.downloader.start_session()
        except Exception:
            pass
        for d in list(self.downloads):
            try:
                if d.get("type") != "URL":
                    continue
                if d.get("status") in ("Completed", "Error"):
                    continue
                d["status"] = "Queued"
                url = d.get("url")
                name = d.get("name")
                save_path = d.get("path") or "downloads"
                did = d.get("id")
                task = asyncio.create_task(self.downloader.download_file(url, did, name, save_path))
                self.download_tasks[did] = task
            except Exception:
                logging.exception("[TermoLoad] Failed to queue resume for download")

        
if __name__ == "__main__":
    # Show loading screen first
    loading = LoadingScreen()
    loading.run()
    
    # Then launch the main app
    app = TermoLoad()
    app.run()
