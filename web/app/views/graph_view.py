import json

from functools import wraps

from app.db.app_db import add_visit
from app.utils import timer
from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    render_template,
    current_app,
    make_response,
)
from loguru import logger

from app.db.graph_db import (
    get_company_by_id,
    get_individual_by_id,
    get_random_company_id,
    search_company_names,
    search_individual_names,
)
from app.extensions import cache
from app.graph import extract_subgraph, load_graph

from app.utils import get_or_create_device_id, set_device_id_cookie


graph_bp = Blueprint("graph", __name__)


def cache_with_node_id():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            device_id = get_or_create_device_id()

            node_id = request.args.get("nodeId")
            cache_key = f"{request.path}:{node_id}"

            cached_response = cache.get(cache_key)
            logger.info(f"Got cached: {bool(cached_response)}")

            if cached_response is None:
                # TODO: setup proper envvars
                CACHE_ENDPOINT_TIMEOUT = int(
                    current_app.config.get("CACHE_DEFAULT_TIMEOUT")
                )
                response = f(*args, **kwargs)
                cache.set(cache_key, response, timeout=CACHE_ENDPOINT_TIMEOUT)
            else:
                response = cached_response

            add_visit(request.path, node_id, device_id)

            if not isinstance(response, current_app.response_class):
                response = make_response(response)

            response = set_device_id_cookie(response, device_id)

            return response

        return decorated_function

    return decorator


@graph_bp.route("/graph")
@timer
@cache_with_node_id()
def graph():
    node_id = request.args.get("nodeId", default="e-1")
    company, individual = None, None
    if node_id.startswith("e-"):
        company_id = node_id.split("-", 1)[1]
        company = get_company_by_id(company_id)
    elif node_id.startswith("i-"):
        individual_id = node_id.split("-", 1)[1]
        individual = get_individual_by_id(individual_id)
    else:
        return render_template("error.html", message="The node ID is not valid")

    try:
        G = load_graph()
        complete_subgraph = extract_subgraph(G, node_id)
    except ValueError as e:
        return render_template("error.html", message=str(e))

    nodes = []
    edges = []

    for node, data in complete_subgraph.nodes(data=True):
        nodes.append(
            {
                "data": {
                    "id": node,
                    "name": data["label"],
                    "type": data["type"],
                    "status": data["status"],
                }
            }
        )

    for source, target, data in complete_subgraph.edges(data=True):
        edges.append(
            {
                "data": {
                    "source": source,
                    "target": target,
                    "relationship": data["relationship"],
                }
            }
        )

    graph_data = json.dumps({"nodes": nodes, "edges": edges})
    return render_template(
        "graph.html",
        center_node=company or individual,
        graph_data=graph_data,
    )


@graph_bp.route("/company/<id>")
def company(id):
    return redirect(url_for("graph.graph", nodeId=f"e-{id}"))


@graph_bp.route("/individual/<id>")
def individual(id):
    return redirect(url_for("graph.graph", nodeId=f"i-{id}"))


@graph_bp.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query", "")
        if not query:
            return redirect(url_for("graph.graph"))

        query = request.form.get("query")
        company_results = search_company_names(query)
        individual_results = search_individual_names(query)
    else:
        query = ""
        company_results = None
        individual_results = None

    return render_template(
        "search.html",
        query=query,
        companies=company_results,
        individuals=individual_results,
    )


@graph_bp.route("/random")
def random_company():
    # TODO cache
    company_id = get_random_company_id()
    return redirect(url_for("graph.company", id=company_id))
