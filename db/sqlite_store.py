from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable
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
        self.db_path = path / DB_NAME

        # create a thread-local storage, where each thread accesses its own connection
        self._local = threading.local()

        if reset:
            self._reset()
            self._init()
        else:
            self._init()
            self._recover()

    def _conn(self) -> sqlite3.Connection:
        # if the current thread does not have a connection
        if not hasattr(self._local, 'conn'):
            conn = sqlite3.connect(
                self.db_path,
                timeout=30,  # wait up to 30s when db is locked
                isolation_level=None,  # manually control transactions and database locks
            )

            conn.execute('PRAGMA journal_mode=WAL')  # WAL: allow reading while another thread is writing
            conn.execute('PRAGMA synchronous=NORMAL')  # NORMAL: reduce disk synchronization frequency
            conn.execute('PRAGMA busy_timeout=30000')  # wait 30000ms when db is locked

            self._local.conn = conn
        return self._local.conn

    def _init(self) -> None:
        def work(conn: sqlite3.Connection) -> None:
            conn.execute('BEGIN IMMEDIATE')  # start a transaction and acquire a write lock
            try:
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS pages (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT
                        ,id INTEGER UNIQUE NOT NULL
                        ,status INTEGER NOT NULL DEFAULT {PAGE_STATUS['PENDING']}
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS taxa (
                        id INTEGER PRIMARY KEY
                        ,parent INTEGER
                        ,category INTEGER
                        ,rank INTEGER
                        ,scientific_name TEXT
                        ,authority_year TEXT
                        ,geological_range TEXT
                        ,english_name TEXT
                    )
                ''')
                conn.execute('''
                    INSERT OR IGNORE INTO taxa VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    14772,
                    -1,
                    CATEGORY['included'],
                    RANK['root'],
                    'Vitae',
                    '',
                    '',
                    'living organisms',
                ))  # insert root 'Vitae'
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS synonyms (
                        parent INTEGER
                        ,category INTEGER
                        ,synonym TEXT
                        ,authority_year TEXT
                        ,PRIMARY KEY (parent, synonym, authority_year)
                    )
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_pages_status_seq
                    ON pages(status, seq)
                ''')
                conn.commit()  # persist changes and release the lock
            except Exception:
                conn.rollback()  # roll back the transaction on error
                raise  # re-raise the original exception

        self._execute(work)

    def _reset(self) -> None:
        def work(conn: sqlite3.Connection) -> None:
            conn.execute('BEGIN IMMEDIATE')
            try:
                conn.execute('DROP TABLE IF EXISTS pages')
                conn.execute('DROP TABLE IF EXISTS taxa')
                conn.execute('DROP TABLE IF EXISTS synonyms')
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        self._execute(work)

    def _recover(self) -> None:
        def work(conn: sqlite3.Connection) -> None:
            conn.execute('BEGIN IMMEDIATE')
            try:
                conn.execute('''
                    UPDATE pages
                    SET status = ?
                    WHERE status = ? OR status = ?
                ''', (
                    PAGE_STATUS['PENDING'],
                    PAGE_STATUS['PROCESSING'],
                    PAGE_STATUS['FAILED'])
                             )  # recover unfinished pages
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        self._execute(work)

    def _execute(
            self,
            func: Callable[[sqlite3.Connection], Any],
            max_retries: int = 5,
    ) -> Any:
        conn = self._conn()
        last_error = None

        for i in range(max_retries):
            try:
                return func(conn)
            except sqlite3.OperationalError as e:
                if 'locked' not in str(e).lower():
                    raise
                last_error = e
                time.sleep(0.1 * (i + 1))

        raise RuntimeError(
            f'{func.__name__}: '
            f'database is locked after {max_retries} retries; '
            f'last_error={last_error}'
        ) from last_error

    def pop(
            self,
            limit: int = 1,
    ) -> list[int]:
        if limit <= 0:
            return []

        def work(conn: sqlite3.Connection) -> list[int]:
            conn.execute('BEGIN IMMEDIATE')
            try:
                cur = conn.execute('''
                    UPDATE pages
                    SET status = ?
                    WHERE id IN (
                        SELECT id
                        FROM pages
                        WHERE status = ?
                        ORDER BY seq
                        LIMIT ?
                    )
                    RETURNING id
                ''', (
                    PAGE_STATUS['PROCESSING'],
                    PAGE_STATUS['PENDING'],
                    limit,
                ))
                rows = cur.fetchall()
                conn.commit()
                return [row[0] for row in rows]
            except Exception:
                conn.rollback()
                raise

        return self._execute(work)

    def push(
            self,
            page_ids: list[int],
    ) -> int:
        if not page_ids:
            return 0

        def work(conn: sqlite3.Connection) -> int:
            conn.execute('BEGIN IMMEDIATE')
            try:
                before = conn.total_changes
                conn.executemany('''
                    INSERT OR IGNORE INTO pages(id, status)
                    VALUES (?, ?)
                ''', [
                    (page_id, PAGE_STATUS['PENDING'])
                    for page_id in page_ids
                ])
                inserted = conn.total_changes - before
                conn.commit()
                return inserted
            except Exception:
                conn.rollback()
                raise

        return self._execute(work)

    def mark_done(
            self,
            page_ids: list[int]
    ) -> int:
        if not page_ids:
            return 0

        def work(conn: sqlite3.Connection) -> int:
            conn.execute('BEGIN IMMEDIATE')
            try:
                before = conn.total_changes
                conn.executemany('''
                    UPDATE pages
                    SET status = ?
                    WHERE id = ?
                ''', [
                    (PAGE_STATUS['DONE'], page_id)
                    for page_id in page_ids
                ])
                updated = conn.total_changes - before
                conn.commit()
                return updated
            except Exception:
                conn.rollback()
                raise

        return self._execute(work)

    def mark_failed(
            self,
            page_ids: list[int]
    ) -> int:
        if not page_ids:
            return 0

        def work(conn: sqlite3.Connection) -> int:
            conn.execute('BEGIN IMMEDIATE')
            try:
                before = conn.total_changes
                conn.executemany('''
                    UPDATE pages
                    SET status = ?
                    WHERE id = ?
                ''', [
                    (PAGE_STATUS['FAILED'], page_id)
                    for page_id in page_ids
                ])
                updated = conn.total_changes - before
                conn.commit()
                return updated
            except Exception:
                conn.rollback()
                raise

        return self._execute(work)

    def write_taxa(
            self,
            items: list[dict]
    ) -> int:
        if not items:
            return 0

        def work(conn: sqlite3.Connection) -> int:
            conn.execute('BEGIN IMMEDIATE')
            try:
                before = conn.total_changes
                conn.executemany('''
                    INSERT OR IGNORE INTO taxa (
                        id
                        ,parent
                        ,category
                        ,rank
                        ,scientific_name
                        ,authority_year
                        ,geological_range
                        ,english_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    (
                        item['id'],
                        item['parent'],
                        CATEGORY.get(item['category']),
                        RANK.get(item['rank']),
                        item['scientific_name'],
                        item['authority_year'],
                        item['geological_range'],
                        item['english_name'],
                    )
                    for item in items
                ])
                inserted = conn.total_changes - before
                conn.commit()
                return inserted
            except Exception:
                conn.rollback()
                raise

        return self._execute(work)

    def write_synonym(
            self,
            items: list[dict]
    ) -> int:
        if not items:
            return 0

        def work(conn: sqlite3.Connection) -> int:
            conn.execute('BEGIN IMMEDIATE')
            try:
                before = conn.total_changes
                conn.executemany('''
                    INSERT OR IGNORE INTO synonyms (
                        parent
                        ,category
                        ,synonym
                        ,authority_year
                    )
                    VALUES (?, ?, ?, ?)
                ''', [
                    (
                        item['parent'],
                        CATEGORY.get(item['category']),
                        item['scientific_name'],
                        item['authority_year'],
                    )
                    for item in items
                ])
                inserted = conn.total_changes - before
                conn.commit()
                return inserted
            except Exception:
                conn.rollback()
                raise

        return self._execute(work)

    def close(self) -> None:
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            del self._local.conn

    def __len__(self) -> int:
        conn = self._conn()
        cur = conn.execute('''
            SELECT COUNT(*)
            FROM pages
            WHERE status = ?
        ''', (
            PAGE_STATUS['PENDING'],
        ))

        return cur.fetchone()[0]
