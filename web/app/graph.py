import networkx as nx

from app.db.graph_db import get_db
from app.extensions import cache


def _fetch_graph_data():
    # TODO: use with block ?
    #
    # conn = sqlite3.connect(str(db_path))
    conn = get_db()
    cursor = conn.cursor()

    # Fetch companies
    cursor.execute("SELECT id, company_name, entity_status FROM companies")
    companies = cursor.fetchall()

    # Fetch individuals
    cursor.execute("SELECT id, name FROM individuals")
    individuals = cursor.fetchall()

    # Fetch company_directors relationships
    cursor.execute("SELECT company_id, individual_id, entity_id FROM company_directors")
    directors = cursor.fetchall()

    # Fetch company_shareholders relationships
    cursor.execute(
        "SELECT company_id, individual_id, entity_id, number_of_shares FROM company_shareholders"
    )
    shareholders = cursor.fetchall()

    # conn.close()

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


@cache.memoize()
def load_graph():
    """Return the NetworkX graph constructed from values in companies database.

    This function is memoized for performance.
    The backing database does not update often so no problem with extended caching.
    """
    companies, individuals, directors, shareholders = _fetch_graph_data()
    return _construct_graph(companies, individuals, directors, shareholders)


@cache.memoize()
def _calculate_subgraph_nodes(G, node_id: str, depth: int, reverse: bool = False):
    """Return list of nodes connected to the given node_id."""
    return list(nx.bfs_tree(G, node_id, depth_limit=depth, reverse=reverse))


def extract_subgraph(G, node_id, depth: int = 1):
    """Return a subgraph for the given node ID.

    NOTE: subgraph can not be memoized because it can not be pickled.
    """
    if node_id not in G:
        err_msg = f"Node {node_id} not found in the graph"
        raise ValueError(err_msg)

    subgraph_nodes = _calculate_subgraph_nodes(G, node_id, depth)
    reverse_subgraph_nodes = _calculate_subgraph_nodes(G, node_id, depth, reverse=True)
    nodes = list(set(subgraph_nodes) | set(reverse_subgraph_nodes))
    return G.subgraph(nodes)
