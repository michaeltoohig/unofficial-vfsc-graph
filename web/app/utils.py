import uuid
import time
import hashlib
from functools import wraps

from flask import request
from loguru import logger


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"{func.__name__} took {execution_time:.4f} seconds to execute")
        return result

    return wrapper


def get_or_create_device_id():
    device_id = request.cookies.get("device_id")

    if not device_id:
        # Generate a new device_id
        base = f"{request.user_agent.string}:{request.remote_addr}"
        device_id = hashlib.sha256(base.encode()).hexdigest()[:32]

        # Combine with a UUID for uniqueness
        device_id = f"{device_id}-{uuid.uuid4().hex[:8]}"

    return device_id


def set_device_id_cookie(response, device_id):
    response.set_cookie(
        "device_id", device_id, max_age=31536000, httponly=True, samesite="Lax"
    )  # 1 year expiry
    return response
