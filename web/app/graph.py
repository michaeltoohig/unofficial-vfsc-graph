import json

from app.db import search_company_names, search_individual_names
from app.graph_utils import extract_subgraph, init_graph
from flask import Blueprint, request, redirect, url_for, render_template


graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/graph")
def graph():
    nodeId = request.args.get("nodeId", default="e-1")

    try:
        G = init_graph()
        complete_graph = extract_subgraph(G, nodeId)
    except ValueError as e:
        return render_template("error.html", message=str(e))

    nodes = []
    edges = []

    for node, data in complete_graph.nodes(data=True):
        nodes.append(
            {
                "data": {
                    "id": node,
                    "name": data["label"],
                    "type": data["type"],
                    "status": data["status"],
                    "lastseen": None,
                }
            }
        )

    for source, target, data in complete_graph.edges(data=True):
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
    return render_template("graph.html.j2", graph_data=graph_data)


@graph_bp.route("/company/<id>")
def company(id):
    return redirect(url_for("graph.graph", nodeId=f"e-{id}"))


@graph_bp.route("/individual/<id>")
def individual(id):
    return redirect(url_for("graph.graph", nodeId=f"i-{id}"))


@graph_bp.route("/search", methods=["POST"])
def search():
    query = request.form.get("query", "")
    if not query:
        return redirect(url_for("graph.graph"))

    query = request.form.get("query")
    company_results = search_company_names(query)
    individual_results = search_individual_names(query)
    results = individual_results
    results.extend(list(company_results))

    return render_template("search.html", query=query, results=results)
