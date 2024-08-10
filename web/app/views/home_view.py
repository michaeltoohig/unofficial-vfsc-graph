from pathlib import Path
import re

from app.db.app_db import get_popular_nodes
from app.db.graph_db import get_company_by_id, get_individual_by_id
from flask import Blueprint, current_app as app
from flask import render_template
import markdown
import markdown.extensions.fenced_code
from markupsafe import Markup
from pygments.formatters.html import HtmlFormatter


home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    nodeIds = get_popular_nodes()
    popular = []
    for nodeId in nodeIds:
        node_type, node_id = nodeId["node_id"].split("-", 1)
        if node_type == "e":
            entity = get_company_by_id(node_id)
            popular.append(entity)
        elif node_type == "i":
            individual = get_individual_by_id(node_id)
            popular.append(individual)

    return render_template("index.html", popular=popular)


@home_bp.route("/about")
def about():
    with Path("HOME.md").open() as fp:
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
            "about.html",
            content=Markup(html),
            styles=Markup(styles),
        )
