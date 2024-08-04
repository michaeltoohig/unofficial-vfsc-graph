import sqlite3
from pathlib import Path

import networkx as nx


def _extract_data(db_path: Path):
    # TODO: use with block ?
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Extract companies
    cursor.execute("SELECT id, company_name, entity_status FROM companies")
    companies = cursor.fetchall()

    # Extract individuals
    cursor.execute("SELECT id, name FROM individuals")
    individuals = cursor.fetchall()

    # Extract company_directors relationships
    cursor.execute("SELECT company_id, individual_id, entity_id FROM company_directors")
    directors = cursor.fetchall()

    # Extract company_shareholders relationships
    cursor.execute(
        "SELECT company_id, individual_id, entity_id, number_of_shares FROM company_shareholders"
    )
    shareholders = cursor.fetchall()

    conn.close()

    return companies, individuals, directors, shareholders


def _construct_graph(companies, individuals, directors, shareholders):
    G = nx.MultiDiGraph()

    # Add company nodes
    company_nodes = []
    for company_id, company_name, entity_status in companies:
        company_nodes.append(company_id)
        G.add_node(
            f"e-{company_id}",
            label=company_name,
            status=entity_status,
            type="entity",
        )

    # Add individual nodes
    individual_nodes = []
    for individual_id, individual_name in individuals:
        individual_nodes.append(individual_id)
        G.add_node(
            f"i-{individual_id}",
            label=individual_name,
            status=None,
            type="individual",
        )

    # Add director edges
    for company_id, individual_id, entity_id in directors:
        if individual_id and individual_id in individual_nodes:
            G.add_edge(
                f"i-{individual_id}",
                f"e-{company_id}",
                relationship="director",
            )
        elif entity_id and entity_id in company_nodes:
            G.add_edge(
                f"e-{entity_id}",
                f"e-{company_id}",
                relationship="director",
            )

    # Calculate shareholder edge weight
    company_shares = {}
    for company_id, individual_id, entity_id, number_of_shares in shareholders:
        if company_id not in company_shares:
            company_shares[company_id] = {}
        if individual_id:
            company_shares[company_id][f"i-{individual_id}"] = number_of_shares
        elif entity_id:
            company_shares[company_id][f"e-{entity_id}"] = number_of_shares
    company_shares_percentages = {}
    for company_id, data in company_shares.items():
        company_shares_percentages[company_id] = {}
        total_shares = sum(map(lambda v: v, data.values()))
        for key, value in data.items():
            try:
                company_shares_percentages[company_id][key] = value / total_shares
            except ZeroDivisionError:
                company_shares_percentages[company_id][key] = 1

    # Add shareholder edges
    for company_id, individual_id, entity_id, _ in shareholders:
        if individual_id and individual_id in individual_nodes:
            weight = company_shares_percentages[company_id][f"i-{individual_id}"]
            G.add_edge(
                f"i-{individual_id}",
                f"e-{company_id}",
                relationship="shareholder",
                weight=weight,
            )
        elif entity_id and entity_id in company_nodes:
            weight = company_shares_percentages[company_id][f"e-{entity_id}"]
            G.add_edge(
                f"e-{entity_id}",
                f"e-{company_id}",
                relationship="shareholder",
                weight=weight,
            )

    return G


def init_graph():
    # TODO: include in container env
    db_path = Path("./local-companies.db")
    companies, individuals, directors, shareholders = _extract_data(db_path)
    return _construct_graph(companies, individuals, directors, shareholders)


def extract_subgraph(G, nodeId):
    if nodeId not in G:
        raise ValueError(f"Node {nodeId} not found in the graph")

    subgraph_nodes_reverse = list(nx.bfs_tree(G, nodeId, reverse=True, depth_limit=1))
    subgraph_nodes = list(nx.bfs_tree(G, nodeId, depth_limit=1))
    nodes = list(set(subgraph_nodes) | set(subgraph_nodes_reverse))
    return G.subgraph(nodes)
