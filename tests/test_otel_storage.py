"""Tests for OpenTelemetry storage layer."""

import tempfile
import time
from pathlib import Path

import pytest

from idlergear.otel_storage import LogEntry, OTelStorage


@pytest.fixture
def storage():
    """Create temporary OTel storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_otel.db"
        storage = OTelStorage(db_path)
        yield storage
        storage.close()


def test_create_schema(storage):
    """Test schema creation."""
    # Check tables exist
    cursor = storage.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    assert "logs" in tables
    assert "logs_fts" in tables
    assert "stats" in tables
    assert "schema_version" in tables


def test_insert_log(storage):
    """Test inserting a log entry."""
    entry = LogEntry(
        timestamp=int(time.time() * 1e9),
        severity="INFO",
        service="test-service",
        message="Test log message",
        attributes={"key": "value", "number": 42},
    )

    log_id = storage.insert(entry)
    assert log_id > 0

    # Retrieve and verify
    retrieved = storage.get_by_id(log_id)
    assert retrieved is not None
    assert retrieved.severity == "INFO"
    assert retrieved.service == "test-service"
    assert retrieved.message == "Test log message"
    assert retrieved.attributes == {"key": "value", "number": 42}


def test_insert_batch(storage):
    """Test batch insert."""
    now = int(time.time() * 1e9)
    entries = [
        LogEntry(
            timestamp=now + i,
            severity="INFO",
            service=f"service-{i}",
            message=f"Message {i}",
            attributes={},
        )
        for i in range(10)
    ]

    ids = storage.insert_batch(entries)
    assert len(ids) == 10
    assert all(id > 0 for id in ids)

    # Verify all inserted
    count = storage.count()
    assert count == 10


def test_query_by_time_range(storage):
    """Test querying by time range."""
    base_time = int(time.time() * 1e9)

    # Insert logs at different times
    for i in range(5):
        storage.insert(
            LogEntry(
                timestamp=base_time + i * 1000000000,  # 1 second apart
                severity="INFO",
                service="test",
                message=f"Message {i}",
                attributes={},
            )
        )

    # Query middle 3
    results = storage.query(
        start_time=base_time + 1000000000, end_time=base_time + 3000000000
    )

    assert len(results) == 3
    assert results[0].message == "Message 3"  # Descending order
    assert results[1].message == "Message 2"
    assert results[2].message == "Message 1"


def test_query_by_severity(storage):
    """Test querying by severity."""
    now = int(time.time() * 1e9)

    # Insert logs with different severities
    for severity in ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]:
        storage.insert(
            LogEntry(
                timestamp=now,
                severity=severity,
                service="test",
                message=f"{severity} message",
                attributes={},
            )
        )

    # Query only errors
    results = storage.query(severity=["ERROR", "FATAL"])
    assert len(results) == 2
    assert all(r.severity in ["ERROR", "FATAL"] for r in results)


def test_query_by_service(storage):
    """Test querying by service."""
    now = int(time.time() * 1e9)

    # Insert logs from different services
    for service in ["goose", "claude-code", "idlergear"]:
        storage.insert(
            LogEntry(
                timestamp=now,
                severity="INFO",
                service=service,
                message=f"{service} message",
                attributes={},
            )
        )

    # Query only goose
    results = storage.query(service="goose")
    assert len(results) == 1
    assert results[0].service == "goose"


def test_full_text_search(storage):
    """Test full-text search."""
    now = int(time.time() * 1e9)

    # Insert logs with various messages
    messages = [
        "authentication failed for user admin",
        "database connection established",
        "authentication succeeded for user bob",
        "file not found error",
    ]

    for msg in messages:
        storage.insert(
            LogEntry(
                timestamp=now, severity="INFO", service="test", message=msg, attributes={}
            )
        )

    # Search for "authentication"
    results = storage.query(search="authentication")
    assert len(results) == 2
    assert all("authentication" in r.message for r in results)


def test_query_by_trace_id(storage):
    """Test querying by trace ID."""
    now = int(time.time() * 1e9)
    trace_id = "trace-123"

    # Insert logs with and without trace ID
    storage.insert(
        LogEntry(
            timestamp=now,
            severity="INFO",
            service="test",
            message="With trace",
            attributes={},
            trace_id=trace_id,
        )
    )
    storage.insert(
        LogEntry(
            timestamp=now,
            severity="INFO",
            service="test",
            message="Without trace",
            attributes={},
        )
    )

    # Query by trace ID
    results = storage.query(trace_id=trace_id)
    assert len(results) == 1
    assert results[0].trace_id == trace_id


def test_count(storage):
    """Test counting logs."""
    now = int(time.time() * 1e9)

    # Insert 10 logs
    for i in range(10):
        storage.insert(
            LogEntry(
                timestamp=now + i,
                severity="INFO" if i < 5 else "ERROR",
                service="test",
                message=f"Message {i}",
                attributes={},
            )
        )

    # Count all
    assert storage.count() == 10

    # Count by severity
    assert storage.count(severity=["ERROR"]) == 5


def test_delete_old_logs(storage):
    """Test deleting old logs."""
    base_time = int(time.time() * 1e9)

    # Insert logs at different times
    for i in range(10):
        storage.insert(
            LogEntry(
                timestamp=base_time + i * 1000000000,
                severity="INFO",
                service="test",
                message=f"Message {i}",
                attributes={},
            )
        )

    # Delete logs older than 5 seconds
    deleted = storage.delete_old_logs(base_time + 5000000000)
    assert deleted == 5

    # Verify remaining
    assert storage.count() == 5


def test_stats(storage):
    """Test statistics storage."""
    stats = {
        "total_logs": 1000,
        "logs_per_second": 42.5,
        "services": ["goose", "claude-code"],
    }

    storage.update_stats(stats)
    retrieved = storage.get_stats()

    assert retrieved["total_logs"] == 1000
    assert retrieved["logs_per_second"] == 42.5
    assert retrieved["services"] == ["goose", "claude-code"]


def test_pagination(storage):
    """Test query pagination."""
    now = int(time.time() * 1e9)

    # Insert 25 logs
    for i in range(25):
        storage.insert(
            LogEntry(
                timestamp=now + i,
                severity="INFO",
                service="test",
                message=f"Message {i}",
                attributes={},
            )
        )

    # Get first page (10 results)
    page1 = storage.query(limit=10, offset=0)
    assert len(page1) == 10
    assert page1[0].message == "Message 24"  # Descending

    # Get second page
    page2 = storage.query(limit=10, offset=10)
    assert len(page2) == 10
    assert page2[0].message == "Message 14"

    # Get third page (partial)
    page3 = storage.query(limit=10, offset=20)
    assert len(page3) == 5
    assert page3[0].message == "Message 4"


def test_task_note_linking(storage):
    """Test linking logs to tasks and notes."""
    now = int(time.time() * 1e9)

    # Insert log that created a task
    entry = LogEntry(
        timestamp=now,
        severity="ERROR",
        service="goose",
        message="Critical error occurred",
        attributes={},
        created_task_id=42,
    )
    storage.insert(entry)

    # Insert log that created a note
    entry2 = LogEntry(
        timestamp=now + 1,
        severity="WARN",
        service="goose",
        message="Interesting finding",
        attributes={},
        created_note_id=123,
    )
    storage.insert(entry2)

    # Retrieve and verify
    logs = storage.query(limit=10)
    assert logs[0].created_note_id == 123
    assert logs[1].created_task_id == 42
