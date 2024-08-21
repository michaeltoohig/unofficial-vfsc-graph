# import multiprocessing
import os

host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "80")
bind_env = os.getenv("BIND", None)
use_bind = bind_env if bind_env else f"{host}:{port}"

# Gunicorn configuration
bind = use_bind
# workers = multiprocessing.cpu_count() * 2 + 1
# Limit 1 worker due to background tasks does not have a writing lock
workers = 1
worker_class = "gthread"
worker_tmp_dir = "/dev/shm"
threads = 4
timeout = 30
keepalive = 2

graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50

# Logging
# accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190


# Server hooks
def on_starting(server):
    print("Server is starting")


def on_exit(server):
    print("Server is shutting down")


def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")


def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
