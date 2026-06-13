from pathlib import Path
import sqlite3
from typing import Optional
from db.abstract_store import *

DB_NAME = 'taxa.db'


class SqliteStore(AbstractStore):
    def __init__(
            self,
            path: str = './data',
            reset: bool = False,
    ) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(path / DB_NAME)

        if reset:
            self._reset()
            self._init()
        else:
            self._init()
            self._recover()

    def _init(self):
        self.conn.execute(f'''
            CREATE TABLE IF NOT EXISTS pages (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER UNIQUE NOT NULL,
                status INTEGER NOT NULL DEFAULT {PAGE_STATUS['PENDING']}
            )
        ''')

        self.conn.execute('''
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
        ''')

        # Insert root 'Vitae' in to table 'taxa'...
        self.conn.execute(f'''
            INSERT OR IGNORE INTO taxa VALUES
            (14772,-1,{CATEGORY['included']},{RANK['root']},'Vitae','','','living organisms')
        ''')

        # Create table 'synonyms' if not exists...
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS synonyms (
                parent INTEGER,
                category INTEGER,
                synonym TEXT,
                authority_year TEXT
            )
        ''')

        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_pages_status_seq
            ON pages(status, seq)
        ''')

        # persist changes
        self.conn.commit()

    def _reset(self):
        self.conn.execute('DROP TABLE IF EXISTS pages')
        self.conn.execute('DROP TABLE IF EXISTS taxa')
        self.conn.execute('DROP TABLE IF EXISTS synonyms')
        self.conn.commit()

    def _recover(self):
        # recover unfinished pages
        self.conn.execute(
            'UPDATE pages SET status = ? WHERE status = ? OR status = ?',
            (PAGE_STATUS['PENDING'], PAGE_STATUS['PROCESSING'], PAGE_STATUS['FAILED'])
        )
        self.conn.commit()

    def pop(self) -> Optional[str]:
        cur = self.conn.execute(f'''
            SELECT id
            FROM pages
            WHERE status = {PAGE_STATUS['PENDING']}
            ORDER BY seq
            LIMIT 1
        ''')
        row = cur.fetchone()

        if row is None:
            return None

        page_id = row[0]

        self.conn.execute(
            'UPDATE pages SET status = ? WHERE id = ?',
            (PAGE_STATUS['PROCESSING'], page_id)
        )
        self.conn.commit()

        return page_id

    def push(self, page_id) -> bool:
        cur = self.conn.execute(
            'INSERT OR IGNORE INTO pages(id, status) VALUES (?, ?)',
            (page_id, PAGE_STATUS['PENDING'])
        )
        self.conn.commit()
        return cur.rowcount == 1

    def mark_done(self, page_id) -> None:
        self.conn.execute(
            'UPDATE pages SET status = ? WHERE id = ?',
            (PAGE_STATUS['DONE'], page_id)
        )
        self.conn.commit()

    def mark_failed(self, page_id) -> None:
        self.conn.execute(
            'UPDATE pages SET status = ? WHERE id = ?',
            (PAGE_STATUS['FAILED'], page_id)
        )
        self.conn.commit()

    def write_taxa(self, item) -> None:
        self.conn.execute('''
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
        ''', (
            item['id'],
            item['parent'],
            CATEGORY.get(item['category']),
            RANK.get(item['rank']),
            item['scientific_name'],
            item['authority_year'],
            item['geological_range'],
            item['english_name'],
        ))
        self.conn.commit()

    # Write a record to table 'synonyms'...
    def write_synonym(self, item) -> None:
        self.conn.execute('''
            INSERT OR IGNORE INTO synonyms (
                parent,
                category,
                synonym,
                authority_year
            )
            VALUES (?, ?, ?, ?)
        ''', (
            item['parent'],
            CATEGORY.get(item['category']),
            item['scientific_name'],
            item['authority_year'],
        ))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __len__(self) -> int:
        cur = self.conn.execute(
            'SELECT COUNT(*) FROM pages WHERE status = ?',
            (PAGE_STATUS['PENDING'],)
        )
        return cur.fetchone()[0]
