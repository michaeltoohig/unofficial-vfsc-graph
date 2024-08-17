import json

from app.db.app_db import get_history, get_popular_nodes
from app.db.graph_db import (
    get_latest_registered_companies,
    get_company_by_id,
    get_db_counter_stats,
    get_individual_by_id,
    get_latest_updated_companies,
    get_oldest_registered_companies,
)
from app.utils import render_md_template
from flask import Blueprint, current_app as app
from flask import render_template


home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    # TODO: cache this page

    # Get counter stats
    counts = get_db_counter_stats()

    # Get popular nodes
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

    faq = [
        {
            "question": "Is this website affiliated with the VFSC?",
            "answer": "No, this website is not affiliated with the VFSC. It is a personal project and a technical demonstration, with no official connection to the VFSC.",
        },
        {
            "question": "How did you get this data?",
            "answer": "The data for this project was gathered from public records available on the VFSC website.",
        },
        {
            "question": "Is the data accurate?",
            "answer": "The data is as accurate as possible, but no assurances are given regarding its accuracy. The information on this website should not be used for any purpose. Always verify data on the official VFSC website.",
        },
        {
            "question": "Why are you missing a company?",
            "answer": "Data is collected periodically, so the information presented may be incomplete or outdated. Missing companies may be added in future updates. You may also be conflating a company name with a trading name.",
        },
        {
            "question": "Why are some people listed twice with different spellings?",
            "answer": "If the VFSC records one person with two different spellings, they will appear as two different individuals here. This reflects how the data is provided by the VFSC.",
        },
        {
            "question": "Why don't you merge two persons into one when you see a misspelled name?",
            "answer": "Merging records would require significant time and effort. This project does not involve curating the data at this level.",
        },
        {
            "question": "Your website shows one person when it should be two different people with the same name.",
            "answer": "There is no way to verify this within the scope of this project. If two people have the same name, they are assumed to be the same person for the purposes of this website.",
        },
        {
            "question": "Why did you make this?",
            "answer": "This project was created to learn new technical skills. It serves as an interesting use-case for those skills, and nothing more.",
        },
    ]

    nodes = [
        {
            "data": {
                "id": 1,
                "name": "Company X",
                "type": "entity",
                "status": "Registered",
            }
        },
        {
            "data": {
                "id": 2,
                "name": "Company Y",
                "type": "entity",
                "status": "Dissolved",
            }
        },
        {
            "data": {
                "id": 3,
                "name": "Person A",
                "type": "individual",
                "status": None,
            }
        },
        {
            "data": {
                "id": 4,
                "name": "Person B",
                "type": "individual",
                "status": None,
            }
        },
        {
            "data": {
                "id": 5,
                "name": "Person C",
                "type": "individual",
                "status": None,
            }
        },
    ]
    edges = [
        {
            "data": {
                "source": 3,
                "target": 1,
                "relationship": "director",
            },
        },
        {
            "data": {
                "source": 3,
                "target": 2,
                "relationship": "director",
            },
        },
        {
            "data": {
                "source": 4,
                "target": 1,
                "relationship": "director",
            },
        },
        {
            "data": {
                "source": 5,
                "target": 1,
                "relationship": "shareholder",
            },
        },
        {
            "data": {
                "source": 2,
                "target": 1,
                "relationship": "shareholder",
            },
        },
    ]

    graph_data = json.dumps({"nodes": nodes, "edges": edges})

    return render_template(
        "index.html", counts=counts, popular=popular, faq=faq, graph_data=graph_data
    )


@home_bp.route("/terms-and-conditions")
def terms():
    return render_md_template("terms-and-conditions.md", title="Terms & Conditions")


@home_bp.route("/privacy-policy")
def privacy():
    return render_md_template("privacy-policy.md", title="Privacy Policy")


@home_bp.route("/list/popular")
def list_popular():
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

    return render_template("list.html", title="Most Popular", items=popular)


@home_bp.route("/list/recently-updated")
def list_updated():
    items = get_latest_updated_companies()
    return render_template("list.html", title="Recently Updated Companies", items=items)


@home_bp.route("/list/newly-registered")
def list_new():
    items = get_latest_registered_companies()
    return render_template("list.html", title="Newly Registered Companies", items=items)


@home_bp.route("/list/oldest-registered")
def list_oldest():
    items = get_oldest_registered_companies()
    return render_template(
        "list.html", title="Oldest Registered Companies", items=items
    )


@home_bp.route("/list/recently-visited")
def list_recent():
    nodeIds = get_history()
    items = []
    for nodeId in nodeIds:
        node_type, node_id = nodeId["node_id"].split("-", 1)
        if node_type == "e":
            entity = get_company_by_id(node_id)
            items.append(entity)
        elif node_type == "i":
            individual = get_individual_by_id(node_id)
            items.append(individual)

    return render_template("list.html", title="Recently Visited", items=items)


# @home_bp.route("/about")
# def about():
#     with Path("HOME.md").open() as fp:
#         formatter = HtmlFormatter(
#             style="solarized-light",
#             full=True,
#             cssclass="codehilite",
#         )
#         styles = f"<style>{formatter.get_style_defs()}</style>"
#         html = (
#             markdown.markdown(fp.read(), extensions=["codehilite", "fenced_code"])
#             .replace(
#                 # Fix relative path for image(s) when rendering README.md on index page
#                 'src="app/',
#                 'src="',
#             )
#             .replace("codehilite", "codehilite p-2 mb-3")
#         )
#
#         def replace_heading(match):
#             level = match.group(1)
#             text = match.group(2)
#             id = text.translate(
#                 str.maketrans(
#                     {
#                         " ": "-",
#                         "'": "",
#                         ":": "",
#                     }
#                 )
#             ).lower()
#             style = "padding-top: 70px; margin-top: -70px;"
#             return f'<h{level} id="{id}" style="{style}">{text}</h{level}>'
#
#         html = re.sub(r"<h([1-3])>(.+)</h\1>", replace_heading, html)
#
#         return render_template(
#             "about.html",
#             content=Markup(html),
#             styles=Markup(styles),
#         )
