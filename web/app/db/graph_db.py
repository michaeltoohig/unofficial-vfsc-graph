import sqlite3
from flask import g, current_app


def get_db():
    db = getattr(g, "_graph_database", None)
    if db is None:
        db = g._graph_database = sqlite3.connect(str(current_app.config["GRAPH_DB"]))
        db.row_factory = sqlite3.Row
    return db


def close_db(e=None):
    db = getattr(g, "_graph_database", None)
    if db is not None:
        db.close()


def search_company_names(q: str):
    db = get_db()
    cursor = db.cursor()

    query = "SELECT id, company_name, entity_status FROM companies WHERE company_name LIKE ?"
    cursor.execute(query, (f"%{q}%",))
    return [
        {
            "id": row[0],
            "type": "company",
            "name": row[1],
            "status": row[2],
        }
        for row in cursor.fetchall()
    ]


def search_individual_names(q: str):
    db = get_db()
    cursor = db.cursor()

    query = "SELECT id, name FROM individuals WHERE name LIKE ?"
    cursor.execute(query, (f"%{q}%",))
    return [
        {
            "id": row[0],
            "type": "individual",
            "name": row[1],
        }
        for row in cursor.fetchall()
    ]


def get_company_by_id(node_id):
    db = get_db()
    query = "SELECT company_name, company_number, company_type, entity_status, registration_date FROM companies WHERE id = ?"
    result = db.execute(query, (node_id,)).fetchone()
    return (
        {
            "id": node_id,
            "type": "company",
            "name": result[0],
            "number": result[1],
            "company_type": result[2],
            "status": result[3],
            "registration_date": result[4],
        }
        if result
        else None
    )


def get_individual_by_id(node_id):
    db = get_db()
    query = "SELECT name FROM individuals WHERE id = ?"
    result = db.execute(query, (node_id,)).fetchone()
    return (
        {
            "id": node_id,
            "type": "individual",
            "name": result[0],
        }
        if result
        else None
    )
