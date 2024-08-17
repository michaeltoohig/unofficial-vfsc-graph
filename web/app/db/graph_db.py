import random
import sqlite3
from flask import g, current_app

from app.extensions import cache


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

    query = "SELECT id, company_name, company_number, company_type, entity_status, registration_date FROM companies WHERE company_name LIKE ?"
    cursor.execute(query, (f"%{q}%",))
    return [
        {
            "id": row[0],
            "type": "company",
            "name": row[1],
            "number": row[2],
            "company_type": row[3],
            "status": row[4],
            "registration_date": row[5],
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
    query = "SELECT company_name, company_number, company_type, entity_status, registration_date, office_address, postal_address, lastseen FROM companies WHERE id = ?"
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
            "office_address": result[5],
            "postal_address": result[6],
            "lastseen": result[7],
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


@cache.memoize()
def get_latest_registered_companies(limit=10):
    db = get_db()
    query = """
        SELECT id, company_name, company_number, company_type, entity_status, registration_date
        FROM companies
        WHERE registration_date IS NOT NULL AND entity_status = "Registered"
        ORDER BY registration_date DESC
        LIMIT ?
    """
    results = db.execute(query, (limit,)).fetchall()
    return [
        {
            "id": result[0],
            "type": "company",
            "name": result[1],
            "number": result[2],
            "company_type": result[3],
            "status": result[4],
            "registration_date": result[5],
        }
        for result in results
    ]


@cache.memoize()
def get_oldest_registered_companies(limit=10):
    db = get_db()
    query = """
        SELECT id, company_name, company_number, company_type, entity_status, registration_date
        FROM companies
        WHERE registration_date IS NOT NULL AND entity_status = "Registered"
        ORDER BY registration_date ASC
        LIMIT ?
    """
    results = db.execute(query, (limit,)).fetchall()
    return [
        {
            "id": result[0],
            "type": "company",
            "name": result[1],
            "number": result[2],
            "company_type": result[3],
            "status": result[4],
            "registration_date": result[5],
        }
        for result in results
    ]


@cache.memoize()
def get_latest_updated_companies(limit=10):
    db = get_db()
    query = """
        SELECT id, company_name, company_number, company_type, entity_status, registration_date
        FROM companies
        WHERE updated_at IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT ?
    """
    results = db.execute(query, (limit,)).fetchall()
    return [
        {
            "id": result[0],
            "type": "company",
            "name": result[1],
            "number": result[2],
            "company_type": result[3],
            "status": result[4],
            "registration_date": result[5],
        }
        for result in results
    ]


@cache.memoize()
def _get_min_max_company_ids():
    db = get_db()
    query = "SELECT MIN(ROWID), MAX(ROWID) FROM companies"
    min_id, max_id = db.execute(query).fetchone()
    return min_id, max_id


@cache.memoize(timeout=15)
def get_random_company_id():
    db = get_db()
    min_id, max_id = _get_min_max_company_ids()

    if min_id is None or max_id is None:
        return None

    while True:
        random_id = random.randint(min_id, max_id)
        query = "SELECT id FROM companies WHERE ROWID = ?"
        result = db.execute(query, (random_id,)).fetchone()

        if result is not None:
            break

    return result[0]


@cache.memoize()
def get_db_counter_stats():
    db = get_db()
    query = "SELECT COUNT(id) FROM individuals"
    individuals_result = db.execute(query).fetchone()

    query = "SELECT COUNT(id) FROM companies"
    companies_result = db.execute(query).fetchone()

    query = "SELECT COUNT(company_id) FROM company_shareholders"
    shareholders_result = db.execute(query).fetchone()

    query = "SELECT COUNT(company_id) FROM company_directors"
    directors_result = db.execute(query).fetchone()

    return {
        "individuals": individuals_result[0],
        "companies": companies_result[0],
        "shareholders": shareholders_result[0],
        "directors": directors_result[0],
    }
