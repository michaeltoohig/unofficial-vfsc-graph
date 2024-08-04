from datetime import datetime
from pathlib import Path
import pickle
import sqlite3

SCRAPED_DATA = "local-companies.pkl"
DB_FILE = "test-local-companies.db"


# Create the SQLite database and tables
def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY,
        company_name TEXT,
        company_number TEXT,
        company_type TEXT,
        entity_type TEXT,
        entity_status TEXT,
        registration_date TEXT,
        annual_filing_month TEXT,
        email_address TEXT,
        office_address TEXT,
        postal_address TEXT,
        total_shares INTEGER
    )
    """
    )

    # cursor.execute(
    #     """
    # CREATE TABLE IF NOT EXISTS entities (
    #     id INTEGER PRIMARY KEY,
    #     name TEXT UNIQUE,
    #     number TEXT,
    #     type TEXT
    # )
    # """
    # )
    #
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS individuals (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS company_directors (
        company_id INTEGER,
        individual_id INTEGER,
        entity_id INTEGER,
        appointed_date TEXT,
        ceased_at TEXT,
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (entity_id) REFERENCES compaies(id),
        FOREIGN KEY (individual_id) REFERENCES individuals(id)
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS company_shareholders (
        company_id INTEGER,
        individual_id INTEGER,
        entity_id,
        appointed_date TEXT,
        ceased_at TEXT,
        number_of_shares INTEGER,
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (entity_id) REFERENCES companies(id),
        FOREIGN KEY (individual_id) REFERENCES individuals(id)
    )
    """
    )

    # cursor.execute(
    #     """
    # CREATE VIRTUAL TABLE fts_names USING fts5(
    #     name,
    #     type,
    #     rowid UNINDEXED
    # );
    #
    # -- Triggers for companies
    # CREATE TRIGGER companies_ai AFTER INSERT ON companies BEGIN
    #     INSERT INTO fts_names(rowid, name, type) VALUES (new.id, new.name, 'company');
    # END;
    #
    # CREATE TRIGGER companies_ad AFTER DELETE ON companies BEGIN
    #     DELETE FROM fts_names WHERE rowid = old.id AND type = 'company';
    # END;
    #
    # CREATE TRIGGER companies_au AFTER UPDATE ON companies BEGIN
    #     UPDATE fts_names SET name = new.name WHERE rowid = old.id AND type = 'company';
    # END;
    #
    # -- Triggers for individuals
    # CREATE TRIGGER individuals_ai AFTER INSERT ON individuals BEGIN
    #     INSERT INTO fts_names(rowid, name, type) VALUES (new.id, new.name, 'individual');
    # END;
    #
    # CREATE TRIGGER individuals_ad AFTER DELETE ON individuals BEGIN
    #     DELETE FROM fts_names WHERE rowid = old.id AND type = 'individual';
    # END;
    #
    # CREATE TRIGGER individuals_au AFTER UPDATE ON individuals BEGIN
    #     UPDATE fts_names SET name = new.name WHERE rowid = old.id AND type = 'individual';
    # END;
    #     """
    # )

    conn.commit()
    conn.close()


# Insert or get individual ID
def get_or_create_individual(cursor, individual):
    cursor.execute("SELECT id FROM individuals WHERE name = ?", (individual["name"],))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        """
    INSERT INTO individuals (name)
    VALUES (?)
    """,
        (individual["name"],),
    )
    return cursor.lastrowid


# Get company ID
def get_company_id(cursor, company_name):
    cursor.execute("SELECT id FROM companies WHERE company_name = ?", (company_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    return None


def get_or_create_entity(cursor, entity):
    cursor.execute(
        "SELECT id FROM companies WHERE company_name = ?", (entity["entity_name"],)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    company_data = dict(
        company_name=entity.get("entity_name"),
        company_number=entity.get("entity_number", ""),
        company_type=None,
        general_details=dict(
            entity_type=entity.get("entity_type", ""),
            entity_status=None,
            registration_date=None,  # datetime(1900, 1, 1, 0, 0),
            annual_filing_month=None,
        ),
        addresses=dict(
            email_address=None,
            office_address=dict(
                current=dict(address=None),
                former=None,
            ),
            postal_address=dict(
                current=dict(address=None),
                former=None,
            ),
        ),
        shareholders=dict(
            total_shares=None,
        ),
    )
    return upsert_company(cursor, company_data)


def upsert_company(cursor, company):
    if "shareholders" in company:
        total_shares = company["shareholders"]["total_shares"]
    else:
        total_shares = 0
        print(company["company_name"])

    company_id = get_company_id(cursor, company["company_name"])
    if company_id is None:
        # Update existing record
        cursor.execute(
            """
        INSERT INTO companies (company_name, company_number, company_type, entity_type, entity_status, registration_date, annual_filing_month, email_address, office_address, postal_address, total_shares)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                company["company_name"],
                company["company_number"],
                company["company_type"],
                company["general_details"]["entity_type"],
                company["general_details"]["entity_status"],
                company["general_details"]["registration_date"],
                company["general_details"]["annual_filing_month"],
                company["addresses"]["email_address"],
                company["addresses"]["office_address"]["current"]["address"],
                company["addresses"]["postal_address"]["current"]["address"],
                total_shares,
            ),
        )
        company_id = cursor.lastrowid
    else:
        # Create new record
        cursor.execute(
            """
            UPDATE companies
            SET company_number = ?, company_type = ?, entity_type = ?,
                entity_status = ?, registration_date = ?, annual_filing_month = ?,
                email_address = ?, office_address = ?, postal_address = ?, total_shares = ?
            WHERE id = ?
        """,
            (
                company["company_name"],
                company["company_number"],
                company["company_type"],
                company["general_details"]["entity_type"],
                company["general_details"]["entity_status"],
                company["general_details"]["registration_date"],
                company["general_details"]["annual_filing_month"],
                company["addresses"]["email_address"],
                company["addresses"]["office_address"]["current"]["address"],
                company["addresses"]["postal_address"]["current"]["address"],
                total_shares,
                company_id,
            ),
        )
    return company_id


# Grab the number_of_shares for a given shareholder
def get_number_of_shares(shares, shareholder):
    for share in shares:
        if share.get("individual_name") == shareholder.get("name") or share.get(
            "entity_name"
        ) == shareholder.get("entity_name"):
            return share["number_of_shares"]
    return 0


# Insert company data
def insert_company_data(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # for record in data:
    #     company = record
    #     name = company.get("company_name", None)
    #     upsert_company(cursor, company)

    for record in data:
        company = record
        name = company.get("company_name", None)
        print(record)
        assert name, "No name@!"
        # if name is None:
        #     continue
        company_id = get_company_id(cursor, name)

        if "directors" in company:
            for director in company["directors"].get("current", []):
                appointed_date = director.get(
                    "appointed_date", datetime(1900, 1, 1, 0, 0)
                )
                if "name" in director:
                    individual_id = get_or_create_individual(cursor, director)
                    cursor.execute(
                        """
                    INSERT INTO company_directors (company_id, individual_id, entity_id, appointed_date, ceased_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            company_id,
                            individual_id,
                            None,
                            appointed_date,
                            None,
                        ),
                    )
                elif "entity_name" in director:
                    entity_id = get_or_create_entity(cursor, director)
                    cursor.execute(
                        """
                    INSERT INTO company_directors (company_id, individual_id, entity_id, appointed_date, ceased_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            company_id,
                            None,
                            entity_id,
                            appointed_date,
                            None,
                        ),
                    )
                else:
                    breakpoint()
                    print("How did we end up here?")

        if "shareholders" in company:
            for shareholder in company["shareholders"].get("current", []):
                number_of_shares = get_number_of_shares(company["shares"], shareholder)
                appointed_date = shareholder.get(
                    "appointed_date", datetime(1900, 1, 1, 0, 0)
                )
                if "name" in shareholder:
                    individual_id = get_or_create_individual(cursor, shareholder)
                    cursor.execute(
                        """
                    INSERT INTO company_shareholders (company_id, individual_id, entity_id, appointed_date, ceased_at, number_of_shares)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            company_id,
                            individual_id,
                            None,
                            appointed_date,
                            None,
                            number_of_shares,
                        ),
                    )
                elif "entity_name" in shareholder:
                    entity_id = get_or_create_entity(cursor, shareholder)
                    if entity_id is None or entity_id == "":
                        breakpoint()
                        print("how")
                    cursor.execute(
                        """
                    INSERT INTO company_shareholders (company_id, individual_id, entity_id, appointed_date, ceased_at, number_of_shares)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            company_id,
                            None,
                            entity_id,
                            appointed_date,
                            None,
                            number_of_shares,
                        ),
                    )
                else:
                    breakpoint()
                    print("How did we end up here?")

    conn.commit()
    conn.close()


def load_pickle_data(file_path):
    return pickle.loads(Path(file_path).read_bytes())


# Main function to create database and load data
def main():
    data = load_pickle_data(SCRAPED_DATA)
    create_database()
    insert_company_data(data)


if __name__ == "__main__":
    main()
