import asyncio
from app import RealDownloader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

async def main():
    class DummyApp:
        def __init__(self):
            self.downloads = []
            class FakeTable:
                def update_cell(self, *args, **kwargs):
                    pass
            self.downloads_table = FakeTable()
    app = DummyApp()
    dl = RealDownloader(app)
    app.downloads.append({"id": 1, "progress":0.0, "speed":"0 B/s","eta":"--","status":"Queued"})
    ok = await dl.download_file('https://httpbin.org/bytes/1024', 1, 'test.bin', 'downloads')
    logging.info(f'download finished {ok}')

asyncio.run(main())
