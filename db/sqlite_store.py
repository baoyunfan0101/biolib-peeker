from pathlib import Path
import sqlite3
from typing import Optional
from db.abstract_store import *

PAGE_STATUS = {
    "PENDING": 0,
    "PROCESSING": 1,
    "DONE": 2,
    "FAILED": 3,
}

RANK = {  # sorted by hierarchy
    'root': 1,
    'domain': 30,
    'superregnum': 50,
    'regnum': 51,
    'subregnum': 52,
    'system': 10,
    'kingdom': 60,
    'divisio': 70,
    'subdivisio': 80,
    'superphylum': 100,
    'phylum': 101,
    'subphylum': 102,
    'infraphylum': 103,
    'superclassis': 200,
    'class': 201,
    'subclass': 202,
    'infraclass': 203,
    'cohor': 250,
    'superorder': 300,
    'order': 301,
    'suborder': 302,
    'infraorder': 303,
    'parvorder': 304,
    'falanga': 350,
    'superfamily': 400,
    'family': 401,
    'subfamily': 402,
    'supertribus': 450,
    'tribus': 451,
    'subtribus': 452,
    'intergeneric': 500,
    'genus': 501,
    'subgenus': 502,
    'section': 503,
    'species': 601,
    'subspecies': 610,
    'varietas': 620,
    'form': 621,
    'cultivar': 622,
    'agregate': 730,
    'chimera': 731,
    'group': 740,
    'hybrid': 750,
}

DB_NAME = "taxa.db"


class SqliteStore(AbstractStore):
    def __init__(
            self,
            path: str = "./data",
            reset: bool = False,
    ) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(path / DB_NAME)

        if reset:
            self._reset_table()

        self._init_tables()

    def _reset_table(self):
        self.conn.execute("DROP TABLE IF EXISTS pages")
        self.conn.execute("DROP TABLE IF EXISTS taxa")
        self.conn.execute("DROP TABLE IF EXISTS synonym")
        self.conn.commit()

    def _init_tables(self):
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS pages (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER UNIQUE NOT NULL,
                status INTEGER NOT NULL DEFAULT {PAGE_STATUS["PENDING"]}
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS taxa (
                id INTEGER PRIMARY KEY,
                parent INTEGER,
                category INTEGER,
                rank INTEGER,
                scientific_name TEXT,
                authority_year TEXT,
                geological_range TEXT,
                english_name TEXT
            )
        """)

        # Insert root `Vitae` in to table `taxa`...
        self.conn.execute(f"""INSERT OR IGNORE INTO taxa VALUES (14772,-1,
            {CATEGORY['included']},{RANK['root']},'Vitae','','','living organisms')""")

        # Create table `synonym` if not exists...
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS synonym (
                parent INTEGER,
                category INTEGER,
                synonym TEXT,
                authority_year TEXT
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_status_seq
            ON pages(status, seq)
        """)

        # recover unfinished pages
        self.conn.execute(
            "UPDATE pages SET status = ? WHERE status = ? OR status = ?",
            (PAGE_STATUS["PENDING"], PAGE_STATUS["PROCESSING"], PAGE_STATUS['FAILED'])
        )

        # persist changes
        self.conn.commit()

    def pop(self) -> Optional[str]:
        cur = self.conn.execute(f"""
            SELECT id
            FROM pages
            WHERE status = {PAGE_STATUS['PENDING']}
            ORDER BY seq
            LIMIT 1
        """)
        row = cur.fetchone()

        if row is None:
            return None

        page_id = row[0]

        self.conn.execute(
            "UPDATE pages SET status = ? WHERE id = ?",
            (PAGE_STATUS["PROCESSING"], page_id)
        )
        self.conn.commit()

        return page_id

    def push(self, page_id) -> bool:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO pages(id, status) VALUES (?, ?)",
            (page_id, PAGE_STATUS["PENDING"])
        )
        self.conn.commit()
        return cur.rowcount == 1

    def mark_done(self, page_id) -> None:
        self.conn.execute(
            "UPDATE pages SET status = ? WHERE id = ?",
            (PAGE_STATUS["DONE"], page_id)
        )
        self.conn.commit()

    def mark_failed(self, page_id) -> None:
        self.conn.execute(
            "UPDATE pages SET status = ? WHERE id = ?",
            (PAGE_STATUS["FAILED"], page_id)
        )
        self.conn.commit()

    def write(self, item) -> None:
        self.conn.execute("""
            INSERT OR IGNORE INTO taxa (
                id,
                parent,
                category,
                rank,
                scientific_name,
                authority_year,
                geological_range,
                english_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["id"],
            item["parent"],
            CATEGORY.get(item["category"]),
            RANK.get(item["rank"]),
            item["scientific_name"],
            item["authority_year"],
            item["geological_range"],
            item["english_name"],
        ))
        self.conn.commit()

    # Write a record to table `synonym`...
    def write_synonym(self, item) -> None:
        self.conn.execute("""
            INSERT OR IGNORE INTO synonym (
                parent,
                category,
                synonym,
                authority_year
            )
            VALUES (?, ?, ?, ?)
        """, (
            item["parent"],
            CATEGORY.get(item["category"]),
            item["scientific_name"],
            item["authority_year"],
        ))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __len__(self) -> int:
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE status = ?",
            (PAGE_STATUS["PENDING"],)
        )
        return cur.fetchone()[0]
