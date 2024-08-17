import re
import uuid
import time
import hashlib
from functools import wraps
from pathlib import Path

from flask import request, render_template
from jinja2.exceptions import TemplateNotFound
from loguru import logger
import markdown
import markdown.extensions.fenced_code
from markupsafe import Markup
from pygments.formatters.html import HtmlFormatter


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


def render_md_template(filename, title):
    fp = Path(f"app/pages/{filename}")
    if not fp.exists():
        raise TemplateNotFound(filename)

    with fp.open() as fp:
        formatter = HtmlFormatter(
            style="solarized-light",
            full=True,
            cssclass="codehilite",
        )
        styles = f"<style>{formatter.get_style_defs()}</style>"
        html = (
            markdown.markdown(fp.read(), extensions=["codehilite", "fenced_code"])
            .replace(
                # Fix relative path for image(s) when rendering README.md on index page
                'src="app/',
                'src="',
            )
            .replace("codehilite", "codehilite p-2 mb-3")
        )

        def replace_heading(match):
            level = match.group(1)
            text = match.group(2)
            id = text.translate(
                str.maketrans(
                    {
                        " ": "-",
                        "'": "",
                        ":": "",
                    }
                )
            ).lower()
            style = "padding-top: 70px; margin-top: -70px;"
            return f'<h{level} id="{id}" style="{style}">{text}</h{level}>'

        html = re.sub(r"<h([1-3])>(.+)</h\1>", replace_heading, html)

        return render_template(
            "md_page.html",
            content=Markup(html),
            title=title,
            styles=Markup(styles),
        )
