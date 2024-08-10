from pathlib import Path
from os import environ


class Config:
    """Flask configuration variables."""

    # General Config
    APP_NAME = environ.get("APP_NAME")
    DEBUG = environ.get("FLASK_DEBUG")
    SECRET_KEY = environ.get("SECRET_KEY")

    # Static Assets
    STATIC_FOLDER = "static"
    TEMPLATE_FOLDER = "templates"

    # Caching
    CACHE_TYPE = "FileSystemCache"
    CACHE_DIR = environ["CACHE_DIR"]  # , "/app/cache")
    CACHE_DEFAULT_TIMEOUT = int(environ.get("CACHE_TIMEOUT", 300))

    # Logging
    LOGS_DIR = environ["LOGS_DIR"]  # , "/app/logs")

    DATA_DIR = environ["DATA_DIR"]  # , "/app/data")
    _APP_DB_FILE = environ["APP_DB_FILE"]
    APP_DB = Path(DATA_DIR) / _APP_DB_FILE
    _GRAPH_DB_FILE = environ["GRAPH_DB_FILE"]
    GRAPH_DB = Path(DATA_DIR) / _GRAPH_DB_FILE
