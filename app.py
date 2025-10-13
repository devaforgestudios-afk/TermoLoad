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
import time
import tkinter as tk
import tkinter.filedialog
import logging

# Configure logging to file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('termoload.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class RealDownloader:
    def __init__(self,app_instance):
        self.app = app_instance
        self.session = None
    async def start_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

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

            # use the provided custom_path (fall back to "downloads")
            download_dir = Path(custom_path or "downloads")
            download_dir.mkdir(parents=True, exist_ok=True)
            filepath = download_dir / filename

            async with self.session.get(url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    start_time = time.time()

                    async with aiofiles.open(filepath, 'wb') as file:
                        async for chunk in response.content.iter_chunked(8192):
                            await file.write(chunk)
                            downloaded += len(chunk)

                            progress = downloaded/ total_size if total_size > 0 else 0
                            elapsed = time.time() - start_time
                            speed = downloaded/elapsed if elapsed > 0 else 0
                            eta = (total_size - downloaded) / speed if speed>0 else 0

                            self.update_download_progress(download_id, progress, speed, eta,"Downloading")
                            await asyncio.sleep(0.01)

                    self.update_download_progress(download_id, 1.0, 0, 0,"Completed")
                    return True
                else:
                    self.update_download_progress(download_id, 0.0, 0, 0,f"Error:{response.status}")
                    return False
        except Exception as e:
            logging.exception(f"[TermoLoad] download_file exception id={download_id}: {e}")
            self.update_download_progress(download_id, 0, 0, 0, f"Error:{str(e)}")
            return False
    def update_download_progress(self,download_id:int,progress:float,speed:float,eta:float,status:str):
        for i, download in enumerate(self.app.downloads):
            if download["id"] == download_id:
                logging.debug(f"[TermoLoad] update progress id={download_id} {int(progress*100)}% status={status}")
                download["progress"] = progress
                download["speed"] = self.format_speed(speed)
                download["eta"] = self.format_time(eta)
                download["status"] = status

                try:
                    row_key = download.get("row_key", i)
                    self.app.downloads_table.update_cell(row_key, 3, f"{int(progress*100)}%")
                    self.app.downloads_table.update_cell(row_key, 4, download["speed"])
                    self.app.downloads_table.update_cell(row_key, 5, status)
                    self.app.downloads_table.update_cell(row_key, 6, download["eta"])
                except Exception:
                    # fallback to index if row key doesn't work for this DataTable
                    try:
                        self.app.downloads_table.update_cell(i, 3, f"{int(progress*100)}%")
                        self.app.downloads_table.update_cell(i, 4, download["speed"])
                        self.app.downloads_table.update_cell(i, 5, status)
                        self.app.downloads_table.update_cell(i, 6, download["eta"])
                    except Exception:
                        logging.exception("[TermoLoad] update_download_progress: failed to update table cells")
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
        width: 60;
        height:15;
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
            yield DataTable(id="downloads_table")
            yield Static("⚙️ Settings will go here", id="settings_panel")
            yield Static("📜 Logs will go here", id="logs_panel")
            yield Static("❓ Help/About here", id="help_panel")

        yield Footer()

    async def on_mount(self) -> None:
        self.downloads_table = self.query_one("#downloads_table", DataTable)
        self.settings_panel = self.query_one("#settings_panel", Static)
        self.logs_panel = self.query_one("#logs_panel", Static)
        self.help_panel = self.query_one("#help_panel", Static)

        self.settings_panel.visible = False
        self.logs_panel.visible = False
        self.help_panel.visible = False

        self.downloads_table.add_columns("ID", "Type", "Name", "Progress", "Speed", "Status", "ETA")

        self.downloads = []

    def on_button_pressed(self, event) -> None:
        
        if event.button.id == "btn_add":
            self.push_screen(AddDownloadModal())
            return

        self.downloads_table.visible = False
        self.settings_panel.visible = False
        self.logs_panel.visible = False
        self.help_panel.visible = False

        if event.button.id == "btn_downloads":
            self.downloads_table.visible = True
        elif event.button.id == "btn_settings":
            self.settings_panel.visible = True
        elif event.button.id == "btn_logs":
            self.logs_panel.visible = True
        elif event.button.id == "btn_help":
            self.help_panel.visible = True

        self.refresh()

    def action_add_download(self) -> None:
        """Action for 'a' key binding."""
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
                # add row to DataTable and store row key for later updates
                try:
                    row_key = self.downloads_table.add_row(
                        str(new_entry["id"]),
                        new_entry["type"],
                        new_entry["name"],
                        "0%",
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
                            "0%",
                            "0 B/s",
                            "Queued",
                            "--"
                        )
                    except Exception:
                        logging.exception("[TermoLoad] on_screen_dismissed: failed to add row to table")
                new_entry["row_key"] = row_key
                self.downloads.append(new_entry)
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

    def process_modal_result(self, result: dict):
        """Process the modal result immediately. This helps when on_screen_dismissed isn't emitted in some environments."""
        try:
            logging.info(f"[TermoLoad] process_modal_result called with: {result}")
            if not result or not isinstance(result, dict):
                logging.debug("[TermoLoad] process_modal_result: nothing to do (no result)")
                return

            url = result.get('url')
            custom_path = result.get('path')

            new_id = len(self.downloads) + 1
            d_type = "Torrent" if (url.endswith(".torrent") or url.startswith("magnet:")) else "URL"
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
            # add row and store key
            try:
                row_key = self.downloads_table.add_row(
                    str(new_entry["id"]),
                    new_entry["type"],
                    new_entry["name"],
                    "0%",
                    "0 B/s",
                    "Queued",
                    "--"
                )
                new_entry["row_key"] = row_key
            except Exception:
                logging.exception("[TermoLoad] process_modal_result: failed to add row to table")
                new_entry["row_key"] = len(self.downloads)
            self.downloads.append(new_entry)

            # ensure downloads view visible
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
        except Exception:
            logging.exception("[TermoLoad] process_modal_result: unexpected error")

    async def on_unmount(self) -> None:
        for task in self.download_tasks.values():
            if not task.done():
                task.cancel()
        await self.downloader.close_session()
        
if __name__ == "__main__":
    app = DownloadManager()
    app.run()
