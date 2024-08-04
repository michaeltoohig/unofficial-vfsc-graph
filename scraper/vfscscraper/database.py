import sqlite3
import hashlib
import json
from datetime import datetime, UTC


class DataManager:
    def __init__(self):
        self.current_db = sqlite3.connect("current_state.db")
        self.history_db = sqlite3.connect("change_history.db")
        self.setup_databases()

    def setup_databases(self):
        # Set up current state database
        with self.current_db:
            self.current_db.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

            self.current_db.execute(
                """
                CREATE TABLE IF NOT EXISTS individuals (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE
                )
            """
            )

            self.current_db.execute(
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

            self.current_db.execute(
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

        # Set up change history database
        with self.history_db:
            self.history_db.execute(
                """
                CREATE TABLE IF NOT EXISTS scraping_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    items_processed INTEGER
                )
            """
            )
            self.history_db.execute(
                """
                CREATE TABLE IF NOT EXISTS failed_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    company_number TEXT,
                    error_message TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES scraping_sessions(id)
                )
            """
            )
            self.history_db.execute(
                """
                CREATE TABLE IF NOT EXISTS changed_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_number TEXT,
                    old_data JSON,
                    new_data JSON,
                    timestamp TIMESTAMP,
                )
            """
            )

    def start_scraping_session(self):
        with self.history_db:
            cursor = self.history_db.cursor()
            cursor.execute(
                """
                INSERT INTO scraping_sessions (start_time, items_processed, status)
                VALUES (?, 0, 'in-progress')
            """,
                (datetime.now(UTC),),
            )
            return cursor.lastrowid

    def end_scraping_session(self, session_id, items_processed, status="success"):
        with self.history_db:
            self.history_db.execute(
                """
                UPDATE scraping_sessions
                SET end_time = ?, items_processed = ?, status = ?
                WHERE id = ?
            """,
                (datetime.now(UTC), items_processed, status, session_id),
            )

    def record_failed_item(self, session_id, company_number, error_message):
        with self.history_db:
            self.history_db.execute(
                """
                INSERT INTO failed_items (session_id, company_number, error_message, timestamp)
                VALUES (?, ?, ?, ?)
            """,
                (session_id, company_number, error_message, datetime.now(UTC)),
            )

    """
    ---
    """

    def get_company_old_data(self, company_number):
        cursor = self.history_db.cursor()
        cursor.execute(
            """
            SELECT new_data_hash
            FROM changed_companies
            WHERE company_number = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (company_number,),
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def get_company_id_by_name(self, company_name):
        cursor = self.current_db.cursor()
        cursor.execute(
            "SELECT id FROM companies WHERE company_name = ?", (company_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def upsert_company(self, item):
        company_id = self.get_company_id_by_name(item["company_name"])
        if company_id is None:
            with self.current_db:
                cursor = self.current_db.cursor()
                cursor.execute(
                    """
                INSERT INTO companies (company_name, company_number, company_type, entity_type, entity_status, registration_date, annual_filing_month, email_address, office_address, postal_address, total_shares, lastseen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item["company_name"],
                        item["company_number"],
                        item["company_type"],
                        item["general_details"]["entity_type"],
                        item["general_details"]["entity_status"],
                        item["general_details"]["registration_date"],
                        item["general_details"]["annual_filing_month"],
                        item["addresses"]["email_address"],
                        item["addresses"]["office_address"]["current"]["address"],
                        item["addresses"]["postal_address"]["current"]["address"],
                        item["total_shares"],
                        datetime.now(UTC),
                    ),
                )
                company_id = cursor.lastrowid
        else:
            with self.current_db:
                cursor = self.current_db.cursor()
                cursor.execute(
                    """
                    UPDATE companies
                    SET company_number = ?, company_type = ?, entity_type = ?,
                        entity_status = ?, registration_date = ?, annual_filing_month = ?,
                        email_address = ?, office_address = ?, postal_address = ?, total_shares = ?,
                        lastseen = ?
                    WHERE id = ?
                """,
                    (
                        item["company_name"],
                        item["company_number"],
                        item["company_type"],
                        item["general_details"]["entity_type"],
                        item["general_details"]["entity_status"],
                        item["general_details"]["registration_date"],
                        item["general_details"]["annual_filing_month"],
                        item["addresses"]["email_address"],
                        item["addresses"]["office_address"]["current"]["address"],
                        item["addresses"]["postal_address"]["current"]["address"],
                        item["total_shares"],
                        datetime.now(UTC),
                        company_id,
                    ),
                )
        return company_id

    def _hash_company_data(self, company_data):
        dict_str = json.dumps(company_data)
        return hashlib.sha256(dict_str.encode()).hexdigest()

    def is_data_unchanged(self, old_data, new_data):
        old_data_hash = self._hash_company_data(old_data)
        new_data_hash = self._hash_company_data(new_data)
        return old_data_hash == new_data_hash

    def update_item(self, item):
        company_number = item["company_number"]
        assert company_number, "Company number is missing!"

        old_data = self.get_company_old_data(company_number)

        if old_data and self.is_data_unchanged(old_data, item):
            # Data has not changed; update lastseen
            with self.current_db:
                self.current_db.execute(
                    """
                    UPDATE companies
                    SET lastseen = ?
                    WHERE company_number = ?
                """,
                    (datetime.now(UTC), company_number),
                )
        else:
            # Data has changed or no history exists; update the current db and add to history
            company_id = self.upsert_company(item)
            self.remove_company_relationships(company_id)
            # TODO: reset directors, reset shareholders, upsert individuals
            # - remove old directors and shareholders
            # - def insert_director
            # - def insert_shareholder
            # - def get_or_create_entity
            # - def get_or_create_individual
            # Esentially just recreating the func `insert_company_data` from `test-sqlite.py`

            # Add to history
            with self.history_db:
                self.history_db.execute(
                    """
                    INSERT INTO changed_companies (company_number, old_data, new_data, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        company_number,
                        json.dumps(old_data),
                        json.dumps(item),
                        datetime.now(UTC),
                    ),
                )

    def get_or_create_entity(self, entity):
        pass

    def get_or_create_individual(self, individual):
        pass

    def _hash_company_data(self, company_data):
        dict_str = json.dumps(company_data)
        return hashlib.sha256(dict_str.encode()).hexdigest()

    def remove_company_relationships(self, company_id):
        with self.current_db:
            self.current_db.execute(
                """
                DELETE FROM company_directors
                WHERE company_id = ?
            """,
                (company_id,),
            )
            self.current_db.execute(
                """
                DELETE FROM company_shareholders
                WHERE company_id = ?
            """,
                (company_id,),
            )

    #
    # def _update_item(self, item):
    #     # TODO: check the params and what we will recieve here
    #     # Get the current state of the item
    #     company_id = self.upsert_company(item)
    #     #
    #     company_name = item["company_name"]
    #     company_id = self.get_company_id_by_name(company_name)
    #     if company_id:
    #         # get data -> compare -> update / lastseen
    #         pass
    #     else:
    #         # insert new company
    #         pass
    #
    #     # Update the current state
    #     with self.current_db:
    #         self.current_db.execute(
    #             """
    #             INSERT OR REPLACE INTO companies (company_name, company_number, company_type, entity_type, entity_status, registration_date, annual_filing_month, email_address, office_address, postal_address, total_shares)
    #             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    #         """,
    #             (
    #                 company["company_name"],
    #                 company["company_number"],
    #                 company["company_type"],
    #                 company["general_details"]["entity_type"],
    #                 company["general_details"]["entity_status"],
    #                 company["general_details"]["registration_date"],
    #                 company["general_details"]["annual_filing_month"],
    #                 company["addresses"]["email_address"],
    #                 company["addresses"]["office_address"]["current"]["address"],
    #                 company["addresses"]["postal_address"]["current"]["address"],
    #                 company["total_shares"],
    #             ),
    #         )
    #
    #     # TODO: confirm change at all via some sort of hash of JSON of company scraped
    #
    #     # Log the change
    #     operation = "UPDATE" if current_data else "INSERT"
    #     with self.history_db:
    #         self.history_db.execute(
    #             """
    #             INSERT INTO changes (company_number, operation, old_data, new_data, timestamp)
    #             VALUES (?, ?, ?, ?, ?)
    #         """,
    #             (
    #                 company_number,
    #                 operation,
    #                 json.dumps(current_data),
    #                 json.dumps(new_data),
    #                 datetime.now(),
    #             ),
    #         )

    def get_all_items(self):
        cursor = self.current_db.cursor()
        cursor.execute("SELECT id, data FROM items")
        return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}

    def get_changes(self, start_time=None, end_time=None):
        query = "SELECT * FROM changes WHERE 1=1"
        params = []
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        query += " ORDER BY timestamp"

        cursor = self.history_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def sync_to_web_service(data_manager):
    # This function would be responsible for sending the current state to the web service
    current_state = data_manager.get_all_items()
    # Implement the logic to send current_state to the web service
    # This could be an API call, file transfer, etc.
    print(f"Syncing {len(current_state)} items to web service")


# Usage example
if __name__ == "__main__":
    data_manager = DataManager()

    # Start a scraping session
    session_id = data_manager.start_scraping_session()

    # Simulate scraping and updating items
    data_manager.update_item("item1", {"name": "Item 1", "value": 100})
    data_manager.update_item("item2", {"name": "Item 2", "value": 200})
    data_manager.update_item(
        "item1", {"name": "Item 1", "value": 150}
    )  # Update existing item

    # End the scraping session
    data_manager.end_scraping_session(session_id, 3)

    # Sync the current state to the web service
    sync_to_web_service(data_manager)

    # Retrieve and print changes
    changes = data_manager.get_changes()
    for change in changes:
        print(f"Change: {change}")
