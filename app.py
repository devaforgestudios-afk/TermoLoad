from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Button ,Input, Label
from textual.containers import Container, Horizontal ,  Vertical
from textual.screen import ModalScreen
import random
import asyncio
import aiohttp
import aiofiles
import os
from pathlib import Path
from urllib.parse import urlparse
import json
import time
import tkinter as tk
import tkinter.filedialog
import sys
import subprocess
import logging
from collections import deque
from typing import Optional, Dict, Any, List
try:
    import yt_dlp as ytdlp
except Exception:
    ytdlp = None

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('termoload.log', encoding='utf-8')
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
                # Let yt-dlp use the actual video title
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
                    # Range Not Satisfiable: check if our local file is already complete or invalid
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
                        # Our local file already has the full size; mark as completed
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

                    # Otherwise, remove the partial (or truncate) and retry once
                    try:
                        if filepath.exists():
                            filepath.unlink(missing_ok=True)
                    except Exception:
                        pass
                    # First retry with an explicit Range: bytes=0- (some servers prefer this over no-Range)
                    async with self.session.get(url, headers={"Range": "bytes=0-"}) as r2:
                        if r2.status == 200:
                            total_size = int(r2.headers.get('content-length', 0)) or None
                            open_mode = 'wb'
                            downloaded = 0
                            # proceed to stream below using r2
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
                            # 206 with bytes=0-; treat same as full restart
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
class DownloadManager(App):
    BINDINGS = [("q", "quit", "Quit"),("a","add_download","Add Download")]

    CSS = """
    AddDownloadModal {
        align: center middle;
        }
    
    #modal_container{
        width: 45%;
        height: 55%;
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
    
    #app_welcome{
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 2;
        background: $surface;
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
    #downloads_toolbar {
        padding: 0 1;
    }
    #downloads_toolbar Button {
        margin-right: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.downloader = RealDownloader(self)
        self.download_tasks={}
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True) 

        with Horizontal(id="navbar"):
            yield Button("+ Add Download", id="btn_add", variant="success")
            yield Button("Downloads", id="btn_downloads", variant="primary")
            yield Button("Settings", id="btn_settings")
            yield Button("Logs", id="btn_logs")
            yield Button("Help", id="btn_help")

        with Container(id="main"):
            yield Static("TermoLoad - Download Manager", id="app_welcome")
            with Vertical(id="settings_panel"):
                yield Static("⚙️ Settings", id="settings_title")
                yield Label("Default download folder:")
                with Horizontal():
                    yield Input(id="settings_download_folder", placeholder="e.g., C:\\Users\\You\\Downloads")
                    yield Button("Browse", id="settings_browse", variant="default")
                with Horizontal():
                    yield Button("Save Settings", id="settings_save", variant="primary")
                    yield Button("Cancel", id="settings_cancel", variant="default")

                yield Label("Concurrent downloads:")
                yield Input(id="settings_concurrent", placeholder="3")
                yield Label("Max download speed (KB/s, 0 = unlimited):")
                yield Input(id="settings_speed", placeholder="0")


                yield Label("Shutdown PC when all downlaods complete ")
                yield Input(id="settings_shutdown", placeholder="False")
                yield Label("Allow real system shutdown (dangerous):")
                yield Input(id="settings_allow_real_shutdown", placeholder="False")
            yield Static("No downloads yet. Press 'a' or + Add Download to create one.", id="no_downloads")
            with Horizontal(id="downloads_toolbar"):
                yield Button("Pause Selected", id="btn_pause_sel")
                yield Button("Resume Selected", id="btn_resume_sel")
                yield Button("Pause All", id="btn_pause_all")
                yield Button("Resume All", id="btn_resume_all")
            yield DataTable(id="downloads_table")
            yield Static("📜 Logs will go here", id="logs_panel")
            yield Static("❓ Help/About here", id="help_panel")

        yield Footer()

    async def on_mount(self) -> None:
        self.downloads_table = self.query_one("#downloads_table", DataTable)
        self.downloads_toolbar = self.query_one("#downloads_toolbar", Horizontal)
        self.settings_panel = self.query_one("#settings_panel", Vertical)
        self.logs_panel = self.query_one("#logs_panel", Static)
        self.help_panel = self.query_one("#help_panel", Static)
        self.app_welcome = self.query_one("#app_welcome", Static)
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

        self.downloads_table.add_columns("ID", "Type", "Name", "Progress", "Speed", "Status", "ETA")

        try:
            self.load_settings()
        except Exception:
            logging.exception("[TermoLoad] failed to load settings")

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

    def load_settings(self):
        settings_path = Path("settings.json")
        defaults = {
            "download_folder": str(Path.cwd() / "downloads"),
            "concurrent": 3,
            "max_speed_kb": 0,
            "shutdown_on_complete": False,
            "allow_real_shutdown": False

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
            shutdown_input = self.query_one("#settings_shutdown", Input)
            shutdown_input.value = str(self.settings.get("max_speed_kb", False))
            shutdown_input.value = str(self.settings.get("shutdown_on_complete", False))
        except Exception:
            pass
        try:
            allow_input = self.query_one("#settings_allow_real_shutdown", Input)
            allow_input.value = str(self.settings.get("allow_real_shutdown", False))
        except Exception:
            pass

    async def sync_table_from_downloads(self):
        try:
            rebuild_needed = False
            for i, d in enumerate(self.downloads):
                try:
                    row_key = d.get("row_key", i)
                    # Progress: ASCII bar + two-decimal percent + bytes if available
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
        except Exception:
            logging.exception("[TermoLoad] sync_table_from_downloads failed")

    def on_button_pressed(self, event) -> None:
        
        if event.button.id == "btn_add":
            self.push_screen(AddDownloadModal())
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
                shutdown_input = self.query_one("#settings_shutdown", Input)
                self.settings["download_folder"] = folder_input.value.strip() or str(Path.cwd() / "downloads")
                try:
                    self.settings["concurrent"] = int(concurrent_input.value.strip() or 3)
                except Exception:
                    self.settings["concurrent"] = 3
                try:
                    self.settings["max_speed_kb"] = int(speed_input.value.strip() or 0)
                except Exception:
                    self.settings["max_speed_kb"] = 0
                try:
                    sv = (shutdown_input.value or "").strip().lower()
                    self.settings["shutdown_on_complete"] = sv in ("true", "1", "yes", "y")
                except Exception:
                    self.settings["shutdown_on_complete"] = False
                try:
                    allow_input = self.query_one("#settings_allow_real_shutdown", Input)
                    av = (allow_input.value or "").strip().lower()
                    self.settings["allow_real_shutdown"] = av in ("true", "1", "yes", "y")
                except Exception:
                    pass
                self.save_settings()

            except Exception:
                logging.exception("[TermoLoad] failed to save settings from panel")

        if event.button.id == "settings_cancel":
            try:
                self.load_settings()
            except Exception:
                pass

        try:
            self.downloads_table.visible = False
            self.downloads_table.display = False
            self.downloads_toolbar.visible = False
            self.downloads_toolbar.display = False
        except Exception:
            pass
        try:
            self.settings_panel.visible = False
            self.settings_panel.display = False
        except Exception:
            pass
        try:
            self.logs_panel.visible = False
            self.logs_panel.display = False
        except Exception:
            pass
        try:
            self.help_panel.visible = False
            self.help_panel.display = False
        except Exception:
            pass

        if event.button.id == "btn_downloads":
            try:
                self.downloads_table.visible = True
                self.downloads_table.display = True
                if len(self.downloads) > 0:
                    self.downloads_toolbar.visible = True
                    self.downloads_toolbar.display = True
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
            except Exception:
                pass

        self.refresh()

    def _get_selected_download(self) -> Optional[Dict[str, Any]]:
        """Return the selected download dict based on the table's cursor."""
        try:
            dt = self.downloads_table
            row_key = None
            if hasattr(dt, "cursor_row") and dt.cursor_row is not None:
                row_key = dt.cursor_row
            elif hasattr(dt, "cursor_coordinate") and dt.cursor_coordinate is not None:
                row_key = dt.cursor_coordinate.row
            if row_key is None:
                return None
            for d in self.downloads:
                if d.get("row_key", None) == row_key:
                    return d
            # Fallback by index
            idx = getattr(row_key, "row", None)
            if isinstance(idx, int) and 0 <= idx < len(self.downloads):
                return self.downloads[idx]
            return None
        except Exception:
            return None

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
            if not d or d.get("status") == "Completed":
                return
            t = self.download_tasks.get(download_id)
            if t and not t.done():
                return
            d["status"] = "Queued"
            url = d.get("url")
            name = d.get("name")
            save_path = d.get("path") or "downloads"
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
            if d.get("status") != "Completed":
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
                d_type = "Torrent" if (url.endswith(".torrent") or url.startswith("magnet:")) else "URL"
                # upgrade to Video for known video sites (YouTube)
                try:
                    if d_type == "URL" and RealDownloader.is_video_url(url):
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
                    "status": "Queued",
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
                            "Queued",
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
                self.downloads_table.visible = True
                self.settings_panel.visible = False
                self.logs_panel.visible = False
                self.help_panel.visible = False
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
                        # Set a placeholder name until yt-dlp determines title; it will update item["name"]
                        try:
                            for item in self.downloads:
                                if item.get("id") == new_id:
                                    item["name"] = item.get("name") or "(resolving title...)"
                                    break
                        except Exception:
                            pass
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
            # final attempt
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
                allow_real = bool(self.settings.get("allow_real_shutdown", False))
                try:
                    if allow_real:
                        if sys.platform.startswith("win"):
                            cmd = ["shutdown", "/s", "/t", "0"]
                        else:
                            cmd = ["shutdown", "-h", "now"]
                        subprocess.Popen(cmd, shell=False)
                        logging.info(f"[TermoLoad] maybe_trigger_shutdown: Shutdown command executed: {' '.join(cmd)}")
                    else:
                        logging.info("[TermoLoad] DEBUG: Shut down (simulated)")
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
            d_type = "Torrent" if (url.endswith(".torrent") or url.startswith("magnet:")) else "URL"
            # upgrade to Video when applicable
            try:
                if d_type == "URL" and RealDownloader.is_video_url(url):
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
                "status": "Queued",
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
                    "Queued",
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
                self.settings_panel.visible = False
                self.logs_panel.visible = False
                self.help_panel.visible = False
            except Exception:
                pass

            if d_type == "URL":
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
                    # Placeholder name until yt-dlp sets the actual title-based name
                    try:
                        for item in self.downloads:
                            if item.get("id") == new_id:
                                item["name"] = item.get("name") or "(resolving title...)"
                                break
                    except Exception:
                        pass
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
        return Path("downloads_state.json")

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
    app = DownloadManager()
    app.run()
