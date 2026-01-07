"""
OpenTelemetry log storage using SQLite.

This module provides a SQLite-based storage layer for OpenTelemetry logs with:
- Full-text search (FTS5)
- Structured attributes (JSON1)
- Time-series indexing
- Auto-archiving and rotation
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from idlergear.config import find_idlergear_root


@dataclass
class LogEntry:
    """Represents a single OTel log entry."""

    timestamp: int  # Unix timestamp in nanoseconds
    severity: str  # DEBUG, INFO, WARN, ERROR, FATAL
    service: str  # Service name (goose, claude-code, etc.)
    message: str  # Log message
    attributes: Dict[str, Any]  # OTel attributes
    trace_id: Optional[str] = None  # Distributed tracing ID
    span_id: Optional[str] = None  # Span context ID
    created_task_id: Optional[int] = None  # Auto-created task
    created_note_id: Optional[int] = None  # Auto-created note
    id: Optional[int] = None  # Database row ID


class OTelStorage:
    """SQLite storage for OpenTelemetry logs."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize OTel storage.

        Args:
            db_path: Path to SQLite database file (default: .idlergear/otel.db)
        """
        if db_path is None:
            root = find_idlergear_root()
            if root is None:
                raise ValueError("Not in an IdlerGear project directory")
            db_path = root / ".idlergear" / "otel.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, isolation_level=None
        )
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")

        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        # Check schema version
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if cursor.fetchone() is None:
            # Create schema from scratch
            self._create_schema()
        else:
            # Check version and migrate if needed
            cursor = self.conn.execute("SELECT version FROM schema_version")
            row = cursor.fetchone()
            if row and row[0] < self.SCHEMA_VERSION:
                self._migrate_schema(row[0])

    def _create_schema(self):
        """Create database schema from scratch."""
        self.conn.executescript(
            """
            -- Schema version tracking
            CREATE TABLE schema_version (
                version INTEGER NOT NULL
            );
            INSERT INTO schema_version (version) VALUES (1);

            -- Main logs table
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                severity TEXT NOT NULL,
                service TEXT NOT NULL,
                message TEXT NOT NULL,
                attributes TEXT,
                trace_id TEXT,
                span_id TEXT,
                created_task_id INTEGER,
                created_note_id INTEGER
            );

            -- Indexes for fast queries
            CREATE INDEX idx_timestamp ON logs(timestamp DESC);
            CREATE INDEX idx_severity ON logs(severity);
            CREATE INDEX idx_service ON logs(service);
            CREATE INDEX idx_trace ON logs(trace_id) WHERE trace_id IS NOT NULL;

            -- Full-text search
            CREATE VIRTUAL TABLE logs_fts USING fts5(
                message,
                content='logs',
                content_rowid='id'
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER logs_fts_insert AFTER INSERT ON logs BEGIN
                INSERT INTO logs_fts(rowid, message) VALUES (new.id, new.message);
            END;

            CREATE TRIGGER logs_fts_delete AFTER DELETE ON logs BEGIN
                DELETE FROM logs_fts WHERE rowid = old.id;
            END;

            CREATE TRIGGER logs_fts_update AFTER UPDATE ON logs BEGIN
                DELETE FROM logs_fts WHERE rowid = old.id;
                INSERT INTO logs_fts(rowid, message) VALUES (new.id, new.message);
            END;

            -- Statistics table for collector metrics
            CREATE TABLE stats (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )

    def _migrate_schema(self, from_version: int):
        """Migrate schema from old version to current.

        Args:
            from_version: Current schema version
        """
        # Future migrations go here
        pass

    def insert(self, entry: LogEntry) -> int:
        """Insert a log entry.

        Args:
            entry: Log entry to insert

        Returns:
            Row ID of inserted entry
        """
        cursor = self.conn.execute(
            """
            INSERT INTO logs (
                timestamp, severity, service, message, attributes,
                trace_id, span_id, created_task_id, created_note_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.timestamp,
                entry.severity,
                entry.service,
                entry.message,
                json.dumps(entry.attributes) if entry.attributes else None,
                entry.trace_id,
                entry.span_id,
                entry.created_task_id,
                entry.created_note_id,
            ),
        )
        return cursor.lastrowid

    def insert_batch(self, entries: List[LogEntry]) -> List[int]:
        """Insert multiple log entries in a transaction.

        Args:
            entries: List of log entries to insert

        Returns:
            List of row IDs
        """
        ids = []
        with self.conn:
            for entry in entries:
                cursor = self.conn.execute(
                    """
                    INSERT INTO logs (
                        timestamp, severity, service, message, attributes,
                        trace_id, span_id, created_task_id, created_note_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.timestamp,
                        entry.severity,
                        entry.service,
                        entry.message,
                        json.dumps(entry.attributes) if entry.attributes else None,
                        entry.trace_id,
                        entry.span_id,
                        entry.created_task_id,
                        entry.created_note_id,
                    ),
                )
                ids.append(cursor.lastrowid)
        return ids

    def query(
        self,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        severity: Optional[List[str]] = None,
        service: Optional[str] = None,
        search: Optional[str] = None,
        trace_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LogEntry]:
        """Query log entries.

        Args:
            start_time: Start timestamp (ns) - inclusive
            end_time: End timestamp (ns) - inclusive
            severity: Filter by severity levels
            service: Filter by service name
            search: Full-text search query
            trace_id: Filter by trace ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching log entries
        """
        conditions = []
        params = []

        if start_time is not None:
            conditions.append("l.timestamp >= ?")
            params.append(start_time)

        if end_time is not None:
            conditions.append("l.timestamp <= ?")
            params.append(end_time)

        if severity:
            placeholders = ",".join("?" * len(severity))
            conditions.append(f"l.severity IN ({placeholders})")
            params.extend(severity)

        if service:
            conditions.append("l.service = ?")
            params.append(service)

        if trace_id:
            conditions.append("l.trace_id = ?")
            params.append(trace_id)

        if search:
            # Use full-text search
            query = """
                SELECT l.* FROM logs_fts f
                JOIN logs l ON f.rowid = l.id
            """
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " AND logs_fts MATCH ?"
            params.append(search)
        else:
            query = "SELECT * FROM logs l"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY l.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(query, params)
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_by_id(self, log_id: int) -> Optional[LogEntry]:
        """Get log entry by ID.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry or None if not found
        """
        cursor = self.conn.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
        row = cursor.fetchone()
        return self._row_to_entry(row) if row else None

    def count(
        self,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        severity: Optional[List[str]] = None,
        service: Optional[str] = None,
    ) -> int:
        """Count log entries matching criteria.

        Args:
            start_time: Start timestamp (ns)
            end_time: End timestamp (ns)
            severity: Filter by severity levels
            service: Filter by service name

        Returns:
            Number of matching entries
        """
        conditions = []
        params = []

        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)

        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        if severity:
            placeholders = ",".join("?" * len(severity))
            conditions.append(f"severity IN ({placeholders})")
            params.extend(severity)

        if service:
            conditions.append("service = ?")
            params.append(service)

        query = "SELECT COUNT(*) FROM logs"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor = self.conn.execute(query, params)
        return cursor.fetchone()[0]

    def delete_old_logs(self, before_timestamp: int) -> int:
        """Delete logs older than specified timestamp.

        Args:
            before_timestamp: Delete logs before this timestamp (ns)

        Returns:
            Number of deleted entries
        """
        cursor = self.conn.execute(
            "DELETE FROM logs WHERE timestamp < ?", (before_timestamp,)
        )
        return cursor.rowcount

    def update_stats(self, stats: Dict[str, Any]):
        """Update collector statistics.

        Args:
            stats: Dictionary of stats to update
        """
        now = int(time.time() * 1e9)
        with self.conn:
            for key, value in stats.items():
                self.conn.execute(
                    """
                    INSERT INTO stats (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (key, json.dumps(value), now),
                )

    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics.

        Returns:
            Dictionary of statistics
        """
        cursor = self.conn.execute("SELECT key, value FROM stats")
        return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}

    def vacuum(self):
        """Vacuum the database to reclaim space."""
        self.conn.execute("VACUUM")

    def close(self):
        """Close database connection."""
        self.conn.close()

    def _row_to_entry(self, row: sqlite3.Row) -> LogEntry:
        """Convert database row to LogEntry.

        Args:
            row: SQLite row

        Returns:
            LogEntry instance
        """
        return LogEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            severity=row["severity"],
            service=row["service"],
            message=row["message"],
            attributes=json.loads(row["attributes"]) if row["attributes"] else {},
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            created_task_id=row["created_task_id"],
            created_note_id=row["created_note_id"],
        )
