import sqlite3
from pathlib import Path


# TODO: add to container env
db_path = Path("./local-companies.db")
app_db_path = Path("./app.db")


def search_company_names(query: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sql_query = "SELECT id, company_name, entity_status FROM companies WHERE company_name LIKE ?"
    cursor.execute(sql_query, (f"%{query}%",))
    potential_matches = [
        {
            "id": row[0],
            "type": "company",
            "name": row[1],
            "status": row[2],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return potential_matches


def search_individual_names(query: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sql_query = "SELECT id, name FROM individuals WHERE name LIKE ?"
    cursor.execute(sql_query, (f"%{query}%",))
    potential_matches = [
        {
            "id": row[0],
            "type": "individual",
            "name": row[1],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return potential_matches
