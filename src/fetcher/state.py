"""
SQLite state store for idempotent fetch.

Stores:
- uid_validity per mailbox (to detect server resets)
- last_processed_uid per (mailbox, uid_validity)
- message_hash -> gmail_message_id (to dedupe when UID/UIDVALIDITY change)
- uid -> gmail_message_id (optional, for quick lookup)
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StateStore:
    """Thread-safe SQLite state for UID tracking and hash-based deduplication."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        if self._conn is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), timeout=30)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS uid_state (
                mailbox TEXT NOT NULL,
                uid_validity INTEGER NOT NULL,
                last_processed_uid INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (mailbox, uid_validity)
            );
            CREATE TABLE IF NOT EXISTS message_hashes (
                message_hash TEXT NOT NULL PRIMARY KEY,
                gmail_message_id TEXT,
                uid_validity INTEGER NOT NULL,
                mailbox TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS uid_to_gmail (
                mailbox TEXT NOT NULL,
                uid_validity INTEGER NOT NULL,
                uid INTEGER NOT NULL,
                gmail_message_id TEXT NOT NULL,
                message_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (mailbox, uid_validity, uid),
                FOREIGN KEY (message_hash) REFERENCES message_hashes(message_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_uid_to_gmail_hash ON uid_to_gmail(message_hash);
        """)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_last_processed_uid(self, mailbox: str, uid_validity: int) -> Optional[int]:
        """Return last processed UID for this mailbox and UIDVALIDITY, or None."""
        self.connect()
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT last_processed_uid FROM uid_state WHERE mailbox = ? AND uid_validity = ?",
            (mailbox, uid_validity),
        ).fetchone()
        return int(row[0]) if row else None

    def set_last_processed_uid(self, mailbox: str, uid_validity: int, uid: int) -> None:
        """Update last processed UID (call after successful Gmail import and ISP delete)."""
        self.connect()
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO uid_state (mailbox, uid_validity, last_processed_uid, updated_at)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT (mailbox, uid_validity) DO UPDATE SET
                last_processed_uid = excluded.last_processed_uid,
                updated_at = datetime('now', 'localtime')
            """,
            (mailbox, uid_validity, uid),
        )
        self._conn.commit()

    def seen_hash(self, message_hash: str) -> bool:
        """Return True if we have already imported a message with this SHA256 hash."""
        self.connect()
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT 1 FROM message_hashes WHERE message_hash = ?",
            (message_hash,),
        ).fetchone()
        return row is not None

    def record_import(
        self,
        message_hash: str,
        gmail_message_id: str,
        mailbox: str,
        uid_validity: int,
        uid: int,
    ) -> None:
        """Record a successful import: hash -> Gmail ID and UID -> Gmail ID."""
        self.connect()
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT OR IGNORE INTO message_hashes (message_hash, gmail_message_id, uid_validity, mailbox, created_at)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (message_hash, gmail_message_id, uid_validity, mailbox),
        )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO uid_to_gmail (mailbox, uid_validity, uid, gmail_message_id, message_hash, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (mailbox, uid_validity, uid, gmail_message_id, message_hash),
        )
        self._conn.commit()

    def get_last_fetch_time(self, mailbox: str, uid_validity: int) -> Optional[str]:
        """Return last updated_at for this mailbox/uid_validity (for UI)."""
        self.connect()
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT updated_at FROM uid_state WHERE mailbox = ? AND uid_validity = ?",
            (mailbox, uid_validity),
        ).fetchone()
        return row[0] if row else None

    def get_last_fetch_time_any(self, mailbox: str) -> Optional[tuple[str, int]]:
        """Return (updated_at, uid_validity) for the most recent row for this mailbox (for UI)."""
        self.connect()
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT updated_at, uid_validity FROM uid_state WHERE mailbox = ? ORDER BY updated_at DESC LIMIT 1",
            (mailbox,),
        ).fetchone()
        return (row[0], row[1]) if row else None
