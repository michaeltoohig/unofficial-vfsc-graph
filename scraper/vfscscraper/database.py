import sqlite3
import hashlib
import json
from datetime import datetime, UTC


class DataManager:
    def __init__(self):
        # self.logger = logger
        self.current_db = sqlite3.connect("xxx_current_state.db")
        self.history_db = sqlite3.connect("xxx_change_history.db")
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
                    timestamp TIMESTAMP
                )
            """
            )

    def execute_query(self, db, query, params=None):
        try:
            with db:
                cursor = db.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.lastrowid
        except sqlite3.Error as e:
            # self.logger.error(f"Database error: {e}")
            raise

    def start_scraping_session(self):
        query = """
        INSERT INTO scraping_sessions (start_time, items_processed, status)
        VALUES (?, 0, 'in-progress')
        """
        return self.execute_query(self.history_db, query, (datetime.now(UTC),))

    def end_scraping_session(self, session_id, items_processed, status="success"):
        query = """
        UPDATE scraping_sessions
        SET end_time = ?, items_processed = ?, status = ?
        WHERE id = ?
        """
        self.execute_query(
            self.history_db,
            query,
            (datetime.now(UTC), items_processed, status, session_id),
        )

    def record_failed_item(self, session_id, company_number, error_message):
        query = """
        INSERT INTO failed_items (session_id, company_number, error_message, timestamp)
        VALUES (?, ?, ?, ?)
        """
        self.execute_query(
            self.history_db,
            query,
            (session_id, company_number, error_message, datetime.now(UTC)),
        )

    def get_company_last_known_data(self, company_number):
        query = """
        SELECT new_data
        FROM changed_companies
        WHERE company_number = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """
        with self.history_db:
            cursor = self.history_db.cursor()
            cursor.execute(query, (company_number,))
            result = cursor.fetchone()
        return json.loads(result[0]) if result else None

    def get_company_id_by_name(self, company_name):
        """Fetch company by name.

        We have to assume VFSC is verifying names are unique and spelled correctly
        which is not always true for the latter.

        However, shareholders and directors are only referenced by name so this is
        the best option to associate a known company in these cases.
        """
        query = "SELECT id FROM companies WHERE company_name = ?"
        with self.current_db:
            cursor = self.current_db.cursor()
            cursor.execute(query, (company_name,))
            result = cursor.fetchone()
        return result[0] if result else None

    def insert_company(
        self,
        company_data,
    ):
        """
        Insert a new company.

        Only `company_name` is required because a company may be
        discovered as a director or shareholder of another company
        and we don't yet have more information.
        """
        query = """
        INSERT INTO companies (company_name, company_number, company_type, entity_type, 
        entity_status, registration_date, annual_filing_month, email_address, 
        office_address, postal_address, total_shares, lastseen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            company_data.get("company_name"),
            company_data.get("company_number", None),
            company_data.get("company_type", None),
            company_data.get("entity_type", None),
            company_data.get("entity_status", None),
            company_data.get("registration_date", None),
            company_data.get("annual_filing_month", None),
            company_data.get("email_address", None),
            company_data.get("office_address", None),
            company_data.get("postal_address", None),
            company_data.get("total_shares", None),
            datetime.now(UTC),
        )
        return self.execute_query(self.current_db, query, params)
        # with self.current_db:
        #     cursor = self.current_db.cursor()
        #     cursor.execute(
        #         """
        #         INSERT INTO companies (company_name, company_number, company_type, entity_type, entity_status, registration_date, annual_filing_month, email_address, office_address, postal_address, total_shares, lastseen)
        #         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        #     """,
        #         (
        #             company_name,
        #             company_number,
        #             company_type,
        #             entity_type,
        #             entity_status,
        #             registration_date,
        #             annual_filing_month,
        #             email_address,
        #             office_address,
        #             postal_address,
        #             total_shares,
        #             datetime.now(UTC),
        #         ),
        #     )
        #     return cursor.lastrowid

    def update_company(self, company_id, company_data):
        query = """
        UPDATE companies
        SET company_number = ?, company_type = ?, entity_type = ?,
            entity_status = ?, registration_date = ?, annual_filing_month = ?,
            email_address = ?, office_address = ?, postal_address = ?, total_shares = ?,
            lastseen = ?
        WHERE id = ?
        """
        params = (
            company_data["company_number"],
            company_data["company_type"],
            company_data["general_details"]["entity_type"],
            company_data["general_details"]["entity_status"],
            company_data["general_details"]["registration_date"],
            company_data["general_details"]["annual_filing_month"],
            company_data["addresses"]["email_address"],
            company_data["addresses"]["office_address"]["current"]["address"],
            company_data["addresses"]["postal_address"]["current"]["address"],
            company_data["total_shares"],
            datetime.now(UTC),
            company_id,
        )
        self.execute_query(self.current_db, query, params)

    def upsert_company(self, item):
        company_id = self.get_company_id_by_name(item["company_name"])
        if company_id is None:
            company_id = self.insert_company(item)
        else:
            self.update_company(company_id, item)
        return company_id
        # company_id = self.get_company_id_by_name(item["company_name"])
        # if company_id is None:
        #     company_id = self.insert_company(
        #         company_name=item["company_name"],
        #         company_number=item["company_number"],
        #         company_type=item["company_type"],
        #         entity_type=item["general_details"]["entity_type"],
        #         entity_status=item["general_details"]["entity_status"],
        #         registration_date=item["general_details"]["registration_date"],
        #         annual_filing_month=item["general_details"]["annual_filing_month"],
        #         email_address=item["addresses"]["email_address"],
        #         office_address=item["addresses"]["office_address"]["current"][
        #             "address"
        #         ],
        #         postal_address=item["addresses"]["postal_address"]["current"][
        #             "address"
        #         ],
        #         total_shares=item["total_shares"],
        #     )
        # else:
        #     with self.current_db:
        #         cursor = self.current_db.cursor()
        #         cursor.execute(
        #             """
        #             UPDATE companies
        #             SET company_number = ?, company_type = ?, entity_type = ?,
        #                 entity_status = ?, registration_date = ?, annual_filing_month = ?,
        #                 email_address = ?, office_address = ?, postal_address = ?, total_shares = ?,
        #                 lastseen = ?
        #             WHERE id = ?
        #         """,
        #             (
        #                 item["company_name"],
        #                 item["company_number"],
        #                 item["company_type"],
        #                 item["general_details"]["entity_type"],
        #                 item["general_details"]["entity_status"],
        #                 item["general_details"]["registration_date"],
        #                 item["general_details"]["annual_filing_month"],
        #                 item["addresses"]["email_address"],
        #                 item["addresses"]["office_address"]["current"]["address"],
        #                 item["addresses"]["postal_address"]["current"]["address"],
        #                 item["total_shares"],
        #                 datetime.now(UTC),
        #                 company_id,
        #             ),
        #         )
        # return company_id
        #

    def _hash_company_data(self, company_data):
        dict_str = json.dumps(company_data)
        return hashlib.sha256(dict_str.encode()).hexdigest()

    def is_data_unchanged(self, old_data, new_data):
        """Compare new scraped data against older data to check for any updates."""
        old_data_hash = self._hash_company_data(old_data)
        new_data_hash = self._hash_company_data(new_data)
        return old_data_hash == new_data_hash

    def update_item(self, item):
        company_number = item.get("company_number")
        if not company_number:
            raise ValueError("Company number is missing!")

        old_data = self.get_company_last_known_data(company_number)

        if old_data and self.is_data_unchanged(old_data, item):
            # self.logger.info(f"{company_number} has no changes; updating lastseen")
            self.update_company_lastseen(company_number)
        else:
            company_id = self.upsert_company(item)
            # self.logger.info(f"{company_number} updating relationships")
            self.update_company_relationships(company_id, item)
            self.record_company_change(company_number, old_data, item)

            # self.remove_company_relationships(company_id)
            # if "directors" in item:
            #     for director in item["directors"].get("current", []):
            #         self.create_director_relationsip(company_id, director)
            #     # TODO: former directors can also be added to graph here
            # if "shareholders" in item:
            #     for shareholder in item["shareholders"].get("current", []):
            #         self.create_shareholder_relationship(
            #             company_id,
            #             item["shares"],
            #             shareholder,
            #         )
            #     # TODO: former shareholders can also be added to graph here
            #
            # # Add to history
            # with self.history_db:
            #     self.history_db.execute(
            #         """
            #         INSERT INTO changed_companies (company_number, old_data, new_data, timestamp)
            #         VALUES (?, ?, ?, ?)
            #         """,
            #         (
            #             company_number,
            #             json.dumps(old_data),
            #             json.dumps(item),
            #             datetime.now(UTC),
            #         ),
            #     )
            #

    def update_company_lastseen(self, company_number):
        query = "UPDATE companies SET lastseen = ? WHERE company_number = ?"
        self.execute_query(self.current_db, query, (datetime.now(UTC), company_number))

    def update_company_relationships(self, company_id, item):
        self.remove_company_relationships(company_id)
        if "directors" in item:
            for director in item["directors"].get("current", []):
                self.create_director_relationship(company_id, director)
            # NOTE: former directors can be added to graph here
        if "shareholders" in item:
            for shareholder in item["shareholders"].get("current", []):
                self.create_shareholder_relationship(
                    company_id, item["shares"], shareholder
                )
            # NOTE: former shareholders can be added to graph here

    def record_company_change(self, company_number, old_data, new_data):
        query = """
        INSERT INTO changed_companies (company_number, old_data, new_data, timestamp)
        VALUES (?, ?, ?, ?)
        """
        self.execute_query(
            self.history_db,
            query,
            (
                company_number,
                json.dumps(old_data),
                json.dumps(new_data),
                datetime.now(UTC),
            ),
        )

    def get_or_create_entity(self, entity):
        """Fetch an entity (company) or create a new one."""
        name = entity["entity_name"]
        entity_id = self.get_company_id_by_name(name)
        if not entity_id:
            entity_id = self.insert_company(entity)
        return entity_id

    def get_or_create_individual(self, individual):
        """Fetch an individual or create a new one."""
        name = individual["name"]
        query = "SELECT id FROM individuals WHERE name = ?"
        result = self.execute_query(self.current_db, query, (name,))

        if result:
            return result[0]

        insert_query = "INSERT INTO individuals (name) VALUES (?)"
        return self.execute_query(self.current_db, insert_query, (name,))
        # name = individual["name"]
        # with self.current_db:
        #     cursor = self.current_db.cursor()
        #     cursor.execute(
        #         """
        #         SELECT id FROM individuals WHERE name = ?
        #     """,
        #         (name,),
        #     )
        #     result = cursor.fetchone()
        #     individual_id = result[0] if result else None
        #     if not individual_id:
        #         cursor.execute(
        #             """
        #             INSERT INTO individuals (name) VALUES (?)
        #         """,
        #             (name,),
        #         )
        #         individual_id = cursor.lastrowid
        # return individual_id
        #

    def create_director_relationship(self, company_id, director):
        """Create an entry for a director relationship with the given company."""
        individual_id = None
        entity_id = None
        if "name" in director:
            individual_id = self.get_or_create_individual(director)
        elif "entity_name" in director:
            entity_id = self.get_or_create_entity(director)
        else:
            raise ValueError("Missing director name or entity_name")

        query = """
        INSERT INTO company_directors (company_id, individual_id, entity_id, appointed_date, ceased_at)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (
            company_id,
            individual_id,
            entity_id,
            director.get("appointed_date"),
            director.get("ceased_at"),
        )
        self.execute_query(self.current_db, query, params)

    def get_number_of_shares(self, shares, shareholder):
        """Matches the given shareholder to their number of shares found in a separate table."""
        for share in shares:
            if (share.get("individual_name") == shareholder.get("name")) or (
                share.get("entity_name") == shareholder.get("entity_name")
            ):
                return share["number_of_shares"]
        return 0

    def create_shareholder_relationship(self, company_id, shares, shareholder):
        """Create an entry for a shareholder relationship with the given company."""
        individual_id = None
        entity_id = None
        appointed_date = shareholder.get("appointed_date", None)
        ceased_at = shareholder.get("ceased_at", None)
        number_of_shares = self.get_number_of_shares(shares, shareholder)
        if "name" in shareholder:
            individual_id = self.get_or_create_individual(shareholder)
        elif "entity_name" in shareholder:
            entity_id = self.get_or_create_entity(shareholder)
        else:
            raise ValueError("Missing shareholder name or entity_name")

        number_of_shares = self.get_number_of_shares(shares, shareholder)

        query = """
        INSERT INTO company_shareholders (company_id, individual_id, entity_id, appointed_date, ceased_at, number_of_shares)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            company_id,
            individual_id,
            entity_id,
            shareholder.get("appointed_date"),
            shareholder.get("ceased_at"),
            number_of_shares,
        )
        self.execute_query(self.current_db, query, params)
        #
        # with self.current_db:
        #     self.current_db.execute(
        #         """
        #     """,
        #         (
        #             company_id,
        #             individual_id,
        #             entity_id,
        #             appointed_date,
        #             ceased_at,
        #             number_of_shares,
        #         ),
        #     )
        #

    def remove_company_relationships(self, company_id):
        """Remove all relationships with the given company.

        When a company has updated we rewrite all the relationships which
        requires removing and recreate the relationships as its easy and efficient enough.
        """
        queries = [
            "DELETE FROM company_directors WHERE company_id = ?",
            "DELETE FROM company_shareholders WHERE company_id = ?",
        ]

        for query in queries:
            self.execute_query(self.current_db, query, (company_id,))

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
