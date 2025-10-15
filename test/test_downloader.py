import asyncio
from app import RealDownloader
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class DummyTable:
    def update_cell(self, row, col, value):
        print(f"TABLE_UPDATE row={row} col={col} value={value}")

class DummyApp:
    def __init__(self):
        self.downloads = []
        self.downloads_table = DummyTable()

async def main():
    app = DummyApp()
    app.downloads.append({"id": 1, "progress": 0.0, "speed": "0 B/s", "eta": "--", "status": "Queued"})
    dl = RealDownloader(app)
    url = "https://httpbin.org/bytes/1024"
    logging.info("TEST: starting download")
    ok = await dl.download_file(url, 1, None, custom_path="downloads_test")
    logging.info(f"TEST: download finished {ok}")

if __name__ == '__main__':
    asyncio.run(main())
