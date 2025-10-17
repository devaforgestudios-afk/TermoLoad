from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Button, Input, Label, Checkbox
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
import random
import asyncio
import aiohttp
import threading
from PIL import Image, ImageDraw
import aiofiles
import os
from pathlib import Path
from urllib.parse import urlparse
import json
import time
import tkinter as tk
import tkinter.filedialog
import pystray
import sys
import subprocess
import logging
import ctypes
from collections import deque
from typing import Optional, Dict, Any, List
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

    async def start_session(self):
        if not self.session:
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
            try:
                root = tk.Tk()
                root.withdraw()
                file_path = tkinter.filedialog.askopenfilename(
                    title= "Select Torrent File",
                    filetypes=[("Torrent Files", "*.torrent"), ("All Files", "*.*")]
                )
                if file_path:
                    url_widget = self.query_one("#download_input", Input)
                    url_widget.value = file_path
                root.destroy()
            except Exception:
                pass
        
        elif event.button.id == "browse_folder":
            try:
                root = tk.Tk()
                root.withdraw()
                folder = tkinter.filedialog.askdirectory(title="Select Download folder")
                if folder:
                    path_widget = self.query_one("#save_path", Input)
                    path_widget.value = folder
                root.destroy()
            except:
                pass

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
            try:
                root = tk.Tk()
                root.withdraw()
                folder = tkinter.filedialog.askdirectory(title="Select Download Folder")
                if folder:
                    path_widget = self.query_one("#path_input", Input)
                    path_widget.value = folder
                root.destroy()
            except:
                pass
class TermoLoad(App):
    BINDINGS = [("q", "quit", "Quit"),("a","add_download","Add Download"),("m","minimize_to_tray","Minimize to Tray")]

    CSS = """
    AddDownloadModal {
        align: center middle;
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
    #downloads_toolbar {
        padding: 0 1;
    }
    #downloads_toolbar Button {
        margin-right: 1;
    }
    #status_info{
        padding: 0 1;
        color: $warning;
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
    """
    
    def __init__(self):
        super().__init__()
        self.downloader = RealDownloader(self)
        self.download_tasks={}
        self.tray_icon = None
        self.tray_thread = None
        self._minimized_to_tray = False
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True) 

        with Horizontal(id="navbar"):
            yield Button("+ Add Download", id="btn_add", variant="success")
            yield Button("Downloads", id="btn_downloads", variant="primary")
            yield Button("Settings", id="btn_settings")
            yield Button("Logs", id="btn_logs")
            yield Button("Help", id="btn_help")
            yield Button ("Minimize",id = "btn_minimize", variant="default")

        with Container(id="main"):
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
                
                with Horizontal():
                    yield Button("Cancel", id="settings_cancel", variant="default")
                    yield Button("Save Settings", id="settings_save", variant="primary")
            yield Static("No downloads yet. Press 'a' or + Add Download to create one.", id="no_downloads")
            with Horizontal(id="downloads_toolbar"):
                yield Button("Pause Selected", id="btn_pause_sel")
                yield Button("Resume Selected", id="btn_resume_sel")
                yield Button("Pause All", id="btn_pause_all")
                yield Button("Resume All", id="btn_resume_all")
                yield Button("Delete File", id="btn_delete_file", variant="error")
                yield Button("Remove From List", id="button_remove_list")
                yield Button("Delete + Remove",id="btn_delete_and_remove", variant="error")
            yield DataTable(id="downloads_table")
            yield Static("", id="status_info")
            yield Static("📜 Logs will go here", id="logs_panel")
            yield Static("❓ Help/About here", id="help_panel")

        yield Footer()
    
    def _create_tray_icon_image(self):
        width = 64
        height = 64
        # Use RGBA with transparent background for better tray icon appearance
        image = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        # Draw download icon in green
        dc.rectangle([20,15,44,25], fill="#00ff00")
        dc.polygon([(32,25),(20,35),(44,35)], fill="#00ff00")
        dc.rectangle([28,25,36,45], fill="#00ff00")
        dc.rectangle([20,45,44,50], fill="#00ff00")

        return image

    def _setup_tray_icon(self):
        if pystray is None:
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
        if pystray is None:
            logging.warning("[TermoLoad] pystray not installed, cannot minimize to tray")
            return
        try:
            if not self.tray_icon:
                self._setup_tray_icon()
            
            if self.tray_icon and not self._minimized_to_tray:
                # Non-daemon thread so it keeps running after self.exit()
                self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=False)
                self.tray_thread.start()
                self._minimized_to_tray = True
                logging.info("[TermoLoad] Minimized to system tray")
                
                # Hide the console window from taskbar on Windows
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
                            
                            # Hide the window
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
            
            # Show the console window on Windows before restoring
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
            
            # Restart the app in the same process using os.execv
            # This replaces the current process with a new instance
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

                

    async def on_mount(self) -> None:
        self.downloads_table = self.query_one("#downloads_table", DataTable)
        self.downloads_toolbar = self.query_one("#downloads_toolbar", Horizontal)
        self.settings_panel = self.query_one("#settings_panel", Vertical)
        self.logs_panel = self.query_one("#logs_panel", Static)
        self.help_panel = self.query_one("#help_panel", Static)
        self.status_info = self.query_one("#status_info", Static)
        self.no_downloads = self.query_one("#no_downloads", Static)

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

        self.downloads_table.add_columns("ID", "Type", "Name", "Progress", "Speed", "Status", "ETA")
        # Make row selection explicit and visible
        try:
            self.downloads_table.cursor_type = "row"
            self.downloads_table.show_cursor = True
        except Exception:
            pass

        try:
            self.load_settings()
        except Exception:
            logging.exception("[TermoLoad] failed to load settings")

        # Populate initial Help content
        try:
            self.help_panel.update(self._build_help_text())
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
                    "path": entry.get("path", self.settings.get("download_folder", str(Path.cwd()/"downloads"))),
                    "progress": float(entry.get("progress", 0.0)),
                    "speed": entry.get("speed", "0 B/s"),
                    "status": entry.get("status", "Paused"),
                    "eta": entry.get("eta", "--"),
                    "downloaded_bytes": int(entry.get("downloaded_bytes", 0) or 0),
                    "total_size": int(entry.get("total_size", 0) or 0),
                    "filepath": entry.get("filepath", "")
                }
                try:
                    rk = self.downloads_table.add_row(
                        str(d["id"]), d["type"], d["name"], f"{int(d['progress']*100)}%", d["speed"], d["status"], d["eta"]
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
        defaults = {
            "download_folder": str(Path.cwd() / "downloads"),
            "concurrent": 3,
            "max_speed_kb": 0,
            "shutdown_on_complete": False
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

    async def sync_table_from_downloads(self):
        try:
            rebuild_needed = False
            selected_index = None
            try:
                if hasattr(self.downloads_table, "cursor_row") and self.downloads_table.cursor_row is not None:
                    selected_index = int(self.downloads_table.cursor_row)
            except Exception:
                selected_index = None
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
                    self.downloads_table.update_cell(row_key, 3, f"{bar} {pct}{bytes_txt}")
                    self.downloads_table.update_cell(row_key, 4, d.get('speed', '0 B/s'))
                    self.downloads_table.update_cell(row_key, 5, d.get('status', 'Queued'))
                    self.downloads_table.update_cell(row_key, 6, d.get('eta', '--'))
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
                            rk = self.downloads_table.add_row(
                                str(d.get("id")),
                                d.get("type", ""),
                                d.get("name", ""),
                                f"{bar} {pct}{bytes_txt}",
                                d.get('speed', '0 B/s'),
                                d.get('status', 'Queued'),
                                d.get('eta', '--')
                            )
                            d['row_key'] = rk
                        except Exception:
                            d['row_key'] = None
                    try:
                        if selected_index is not None and self.downloads_table.row_count:
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
            # Update inline status explanation for the selected row
            try:
                sel = self._get_selected_download()
                if sel is not None:
                    txt = self._explain_status(sel.get("status", ""))
                    self.status_info.update(txt)
                else:
                    self.status_info.update("")
            except Exception:
                pass
                # If Help panel is currently visible, refresh it so new errors show up
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
        if event.button.id == "btn_pause_sel":
            self._pause_selected()
            return
        if event.button.id == "btn_resume_sel":
            self._resume_selected()
            return
        if event.button.id == "btn_pause_all":
            self._pause_all()
            return
        if event.button.id == "btn_delete_file":
            asyncio.create_task(self._delete_selected_file_async(delete_partials=True, remove_from_list=False))
            return
        if event.button.id == "button_remove_list":
            self._remove_selected_from_list()
            return
        if event.button.id == "btn_delete_and_remove":
            asyncio.create_task(self._delete_selected_file_async(delete_partials=True, remove_from_list=True))
            return
        if event.button.id == "btn_resume_all":
            self._resume_all()
            return

        if event.button.id == "settings_browse":
            try:
                root = tk.Tk()
                root.withdraw()
                folder = tkinter.filedialog.askdirectory(title="Select Default Download Folder")
                if folder:
                    try:
                        folder_input = self.query_one("#settings_download_folder", Input)
                        folder_input.value = folder
                    except Exception:
                        pass
                root.destroy()
            except Exception:
                pass

        if event.button.id == "settings_save":
            try:
                folder_input = self.query_one("#settings_download_folder", Input)
                concurrent_input = self.query_one("#settings_concurrent", Input)
                speed_input = self.query_one("#settings_speed", Input)
                shutdown_checkbox = self.query_one("#settings_shutdown", Checkbox)
                
                self.settings["download_folder"] = folder_input.value.strip() or str(Path.cwd() / "downloads")
                try:
                    self.settings["concurrent"] = int(concurrent_input.value.strip() or 3)
                except Exception:
                    self.settings["concurrent"] = 3
                try:
                    self.settings["max_speed_kb"] = int(speed_input.value.strip() or 0)
                except Exception:
                    self.settings["max_speed_kb"] = 0
                
                self.settings["shutdown_on_complete"] = shutdown_checkbox.value
                self.save_settings()

            except Exception:
                logging.exception("[TermoLoad] failed to save settings from panel")

        if event.button.id == "settings_cancel":
            try:
                self.load_settings()
            except Exception:
                pass

        if event.button.id in ("btn_downloads", "btn_settings", "btn_logs", "btn_help"):

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
                    self.help_panel.update(self._build_help_text())
                except Exception:
                    pass
                # Hide status info when in Help view
                try:
                    self.status_info.update("")
                except Exception:
                    pass
            except Exception:
                pass

        self.refresh()

    def _get_selected_download(self) -> Optional[Dict[str, Any]]:
        try:
            dt = self.downloads_table
            # Prefer row index; Textual's DataTable uses integer cursor_row for row selection
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
        lines.append("a  Add Download\nq  Quit\nArrow keys select rows on Downloads tab")
        lines.append("")
        lines.append("Common statuses\n----------------")
        lines.append("Downloading  Transfer in progress\nPaused       Task paused or canceled\nQueued       Waiting to start\nCompleted    Finished successfully\nProcessing   Video post-processing (yt-dlp/ffmpeg)")
        lines.append("")
        # Dynamic error list collected from current downloads
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

    def _collect_current_errors(self) -> List[tuple]:
        """Collect a list of current error statuses from downloads.
        Returns list of tuples: (id, name, status_text, hint_text)
        Only includes entries where status starts with 'Error:'.
        """
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
        """Return one-line explanation for the given status string shown inline on Downloads tab."""
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
            return "Completed – File is ready."
        return s

    def _resolve_download_path(self, d: dict) -> Optional[Path]:
        """Resolve the final file path for a download entry.
        Uses stored filepath when available; otherwise derives from path+name.
        """
        try:
            fp = d.get("filepath")
            if fp:
                return Path(fp)
            base_dir = d.get("path") or self.settings.get("download_folder", str(Path.cwd() / "downloads"))
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
                    main_path.unlink()
                    deleted += 1
                except Exception:
                    logging.exception(f"[TermoLoad] failed to delete file: {main_path}")
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

    async def _delete_selected_file_async(self, delete_partials: bool = True, remove_from_list: bool = False) -> None:
        """Safely delete the selected download's file even if it's downloading.
        Cancels any running task, waits a tick, deletes files, and optionally removes the row.
        """
        d = self._get_selected_download()
        if not d:
            return
        did = int(d.get("id"))
        try:
            task = self.download_tasks.get(did)
            if task and not task.done():
                task.cancel()
                await asyncio.sleep(0)
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
            task = self.download_tasks.get(download_id)
            if task and not task.done():
                task.cancel()
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
            if d.get("type") == "Video":
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
        self.push_screen(AddDownloadModal())
           
    
    async def on_screen_dismissed(self, event):
        logging.info(f"[TermoLoad] on_screen_dismissed CALLED: screen={type(event.screen)} result={event.result}")
        if isinstance(event.screen, AddDownloadModal):
            logging.info("[TermoLoad] on_screen_dismissed: AddDownloadModal detected")
            result = event.result
            logging.info(f"[TermoLoad] on_screen_dismissed: result={result}")
            if result and isinstance(result, dict):
                url = result["url"]
                custom_path = result["path"]
                logging.info(f"[TermoLoad] on_screen_dismissed: url={url}, custom_path={custom_path}")
                new_id = len(self.downloads) + 1
                is_torrent =(
                    url.startwith("magnet:") or
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
                logging.info(f"[TermoLoad] on_screen_dismissed: new_entry={new_entry}")
                try:
                    row_key = self.downloads_table.add_row(
                        str(new_entry["id"]),
                        new_entry["type"],
                        new_entry["name"],
                        "0.00%",
                        "0 B/s",
                        "Queued",
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
                if d_type == "Torrent":
                    logging.info(f"[TermoLoad] Queuing torrent download {url}")
                    for d in self.downloads:
                        if d.get("id") == new_id:
                            d["status"] = "Pending"
                            break
                elif d_type == "URL":
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
                for d in self.downloads:
                    if d.get("id") == new_id:
                        d["status"] = "Pending"
                        break
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
        try:
            for d in self.downloads:
                if d.get("status") in ("Downloading", "Queued"):
                    d["status"] = "Paused"
            self.save_downloads_state(force=True)
        except Exception:
            pass

        for task in self.download_tasks.values():
            if not task.done():
                task.cancel()
        await self.downloader.close_session()
    
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
                        "filepath": d.get("filepath", "")
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
            # Backward compatibility: try legacy location in current working directory
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
    app = TermoLoad()
    app.run()
