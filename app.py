from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, DataTable, Static
from textual.widgets._tabbed_content import TabPane
import random
import sys
import os
import time

# Optional imports for future functionality
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import libtorrent as lt
    LIBTORRENT_AVAILABLE = True
except ImportError:
    LIBTORRENT_AVAILABLE = False
class DownloadManagerApp(App):
    CSS = """
    DataTable {
        height: 100%;
        width: 100%;
    }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_downloads", "Refresh"),
    ]

    def on_mount(self) -> None:
        """Called when app starts."""
        # Initialize fake downloads data
        self.fake_downloads = [
            {"id": 1, "type": "URL", "name": "ubuntu.iso", "progress": 0.73, "speed": "2.3 MB/s", "status": "Downloading", "eta": "00:02:13"},
            {"id": 2, "type": "Torrent", "name": "BigBuckBunny.torrent", "progress": 0.42, "speed": "1.2 MB/s", "status": "Downloading", "eta": "00:05:32"},
            {"id": 3, "type": "URL", "name": "report.pdf", "progress": 1.0, "speed": "0.0 MB/s", "status": "Completed", "eta": "Done"},
        ]
        # Get the downloads table widget
        self.downloads_table = self.query_one(DataTable)
        # Start the progress update timer
        self.update_fake_progress_callback()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Downloads"):
                yield self.downloads_view()
            with TabPane("Settings"):
                yield Static("⚙️ Settings will go here")
            with TabPane("Logs"):
                yield Static("📜 Logs will go here")
            with TabPane("Help"):
                yield Static("❓ Help/About here")
        yield Footer()

    def downloads_view(self) -> DataTable:
        """Create the downloads DataTable."""
        table = DataTable()
        table.add_columns("ID", "Type", "Name", "Progress", "Speed", "Status", "ETA")
        table.add_row("1", "URL", "ubuntu.iso", "73%", "2.3 MB/s", "Downloading", "00:02:13")
        table.add_row("2", "Torrent", "BigBuckBunny.torrent", "42%", "1.2 MB/s", "Downloading", "00:05:32")
        table.add_row("3", "URL", "report.pdf", "100%", "0.0 MB/s", "Completed", "Done")
        
        return table

    def update_fake_progress_callback(self):
  
        if hasattr(self, 'fake_downloads') and hasattr(self, 'downloads_table'):
            for row, d in enumerate(self.fake_downloads):
                if d["status"] == "Downloading":
                    d["progress"] = min(1.0, d["progress"] + random.uniform(0.01, 0.05))
                    d["eta"] = "00:0{}:{:02d}".format(random.randint(0, 5), random.randint(0, 59))
                    if d["progress"] >= 1.0:
                        d["progress"] = 1.0
                        d["status"] = "Completed"
                        d["speed"] = "0.0 MB/s"
                        d["eta"] = "Done"
                    try:
                        self.downloads_table.update_cell(row, 3, f"{int(d['progress']*100)}%")
                        self.downloads_table.update_cell(row, 5, d["status"])
                        self.downloads_table.update_cell(row, 6, d["eta"])
                    except Exception:
                        # Handle case where table isn't ready yet
                        pass
        
        # Schedule the next update
        self.set_timer(1.0, self.update_fake_progress_callback)

if __name__ == "__main__":
    # Fix for PyInstaller executable mode
    if getattr(sys, 'frozen', False):
        # Running as executable
        os.environ['TEXTUAL_DRIVER'] = 'windows'
    
    try:
        app = DownloadManagerApp()
        app.run()
    except Exception as e:
        # Fallback for driver issues
        print(f"Error: {e}")
        print("Trying alternative driver...")
        try:
            os.environ['TEXTUAL_DRIVER'] = 'crossterm'
            app = DownloadManagerApp()
            app.run()
        except Exception as e2:
            print(f"Alternative driver also failed: {e2}")
            input("Press Enter to exit...")

class DownloadTask:
    def __init__(self, id , name , type , source):
        self.id = id
        self.name = name
        self.type = type
        self.source = source
        self.progress = 0.0
        self.status = "Queued"
        self.speed= "0 KB/S"


def download_torrent(torrent_path, save_path, task):
    ses = lt.session()
    info = lt.torrent_info(torrent_path)
    h = ses.add_torrent({'ti': info, 'save_path': save_path})
    task.status = "Downloading"

    while not h.is_seed():
        s = h.status()
        task.progress = s.progress*100
        task.speed = f"{s.download_rate / 1000:.2f} KB/s"
        time.sleep(1)
    
    task.status = "Completed"
    task.progress = 100