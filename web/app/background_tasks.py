import atexit
import sqlite3
import queue
import threading
from datetime import datetime, UTC

from loguru import logger


class BackgroundTasks:
    def __init__(self, app=None):
        self.queue = queue.Queue(maxsize=1000)
        self.worker_thread = None
        self.db_path = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.db_path = app.config["APP_DB"]
        app.background_tasks = self
        atexit.register(self.teardown)
        self.start_worker()

    def start_worker(self):
        def worker():
            while True:
                try:
                    task, args = self.queue.get()
                    logger.info(f"Task received: {task} {args}")
                    if task is None:  # Sentinel value to indicate shutdown
                        logger.info(
                            "Got worker teardown sentinel value - Exiting thread"
                        )
                        break
                    if task == "record_visit":
                        self._record_visit(
                            args["node_id"], args["device_id"], args["timestamp"]
                        )
                    elif task == "record_query":
                        self._record_query(
                            args["query"], args["device_id"], args["timestamp"]
                        )
                    self.queue.task_done()
                except Exception as e:
                    logger.exception(f"Error processing task: {e}")

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def teardown(self, exception=None):
        self.queue.put((None, None))  # Send sentinel value to stop the worker
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def record_visit(self, node_id, device_id):
        try:
            logger.debug(f"Recording visit to node {node_id}")
            now = datetime.now(UTC).isoformat()
            self.queue.put_nowait(
                (
                    "record_visit",
                    {"node_id": node_id, "device_id": device_id, "timestamp": now},
                )
            )
            return True
        except queue.Full:
            return False

    def record_query(self, query, device_id):
        try:
            logger.debug(f"Recording query for {query}")
            now = datetime.now(UTC).isoformat()
            self.queue.put_nowait(
                (
                    "record_query",
                    {"query": query, "device_id": device_id, "timestamp": now},
                )
            )
            return True
        except queue.Full:
            return False

    def _record_visit(self, node_id, device_id, timestamp):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO visits (node_id, device_id, timestamp) VALUES (?, ?, ?)",
            (node_id, device_id, timestamp),
        )
        conn.commit()
        conn.close()

    def _record_query(self, query, device_id, timestamp):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO queries (query, device_id, timestamp) VALUES (?, ?, ?)",
            (query, device_id, timestamp),
        )
        conn.commit()
        conn.close()


background_tasks = BackgroundTasks()
