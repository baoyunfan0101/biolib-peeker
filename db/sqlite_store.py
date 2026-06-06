from pathlib import Path
import sqlite3
from typing import Optional
from db.abstract_store import *

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

        self.conn.commit()

    def _init_tables(self):
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS pages (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT UNIQUE NOT NULL,
                status INTEGER NOT NULL DEFAULT {PAGE_STATUS["PENDING"]}
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS taxa (
                id TEXT PRIMARY KEY,
                parent TEXT,
                category TEXT,
                rank TEXT,
                scientific_name TEXT,
                authority_year TEXT,
                geological_range TEXT,
                english_name TEXT
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_status_seq
            ON pages(status, seq)
        """)

        # recover unfinished pages
        self.conn.execute(
            "UPDATE pages SET status = ? WHERE id = ?",
            (PAGE_STATUS["PENDING"], PAGE_STATUS["PROCESSING"])
        )

        # persist changes
        self.conn.commit()

    def pop(self) -> Optional[str]:
        cur = self.conn.execute("""
            SELECT id
            FROM pages
            WHERE status = 0
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
            item["rank"],
            item["scientific_name"],
            item["authority_year"],
            item["geological_range"],
            item["english_name"],
        ))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
