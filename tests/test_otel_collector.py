"""Tests for OpenTelemetry collector."""

import json
import tempfile
import time
from pathlib import Path

import grpc
import pytest
from opentelemetry.proto.collector.logs.v1 import (
    logs_service_pb2,
    logs_service_pb2_grpc,
)
from opentelemetry.proto.common.v1 import common_pb2
from opentelemetry.proto.logs.v1 import logs_pb2

from idlergear.otel_collector import (
    ConsoleExporter,
    ExporterConfig,
    FileExporter,
    OTelCollector,
    create_default_collector,
)
from idlergear.otel_storage import OTelStorage


@pytest.fixture
def temp_storage():
    """Create temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = OTelStorage(Path(tmpdir) / "otel.db")
        yield storage


@pytest.fixture
def temp_log_file():
    """Create temporary log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.jsonl"


def test_console_exporter():
    """Test console exporter."""
    config = ExporterConfig(type="console", min_severity="INFO")
    exporter = ConsoleExporter(config)

    log_data = {
        "timestamp": 1234567890,
        "severity": "INFO",
        "service": "test",
        "message": "Hello",
    }

    # Should export INFO
    assert exporter.should_export("INFO")
    result = exporter.export(log_data)
    assert result is None  # Console doesn't return metadata

    # Should not export DEBUG
    assert not exporter.should_export("DEBUG")


def test_file_exporter(temp_log_file):
    """Test file exporter."""
    config = ExporterConfig(
        type="file", min_severity="DEBUG", config={"path": str(temp_log_file)}
    )
    exporter = FileExporter(config)

    log_data = {
        "timestamp": 1234567890,
        "severity": "ERROR",
        "service": "test",
        "message": "Test error",
        "attributes": {"key": "value"},
    }

    exporter.export(log_data)
    exporter.close()

    # Read file
    assert temp_log_file.exists()
    with open(temp_log_file) as f:
        line = f.readline()
        parsed = json.loads(line)
        assert parsed["message"] == "Test error"
        assert parsed["severity"] == "ERROR"


def test_severity_conversion():
    """Test OTel severity number to string conversion."""
    storage = OTelStorage()
    collector = OTelCollector(storage=storage, exporters=[])

    assert collector._severity_from_number(1) == "DEBUG"
    assert collector._severity_from_number(9) == "INFO"
    assert collector._severity_from_number(13) == "WARN"
    assert collector._severity_from_number(17) == "ERROR"
    assert collector._severity_from_number(21) == "FATAL"


def test_process_log_record(temp_storage):
    """Test processing OTel log record."""
    collector = OTelCollector(storage=temp_storage, exporters=[])

    # Create log record
    log_record = logs_pb2.LogRecord()
    log_record.time_unix_nano = 1234567890000000000
    log_record.severity_number = 17  # ERROR
    log_record.body.string_value = "Test message"

    # Add attributes
    attr = common_pb2.KeyValue()
    attr.key = "test_key"
    attr.value.string_value = "test_value"
    log_record.attributes.append(attr)

    # Add trace context
    log_record.trace_id = bytes.fromhex("12345678901234567890123456789012")
    log_record.span_id = bytes.fromhex("1234567890123456")

    # Process
    result = collector._process_log_record(log_record, "test_service")

    assert result["timestamp"] == 1234567890000000000
    assert result["severity"] == "ERROR"
    assert result["service"] == "test_service"
    assert result["message"] == "Test message"
    assert result["attributes"]["test_key"] == "test_value"
    assert result["trace_id"] == "12345678901234567890123456789012"
    assert result["span_id"] == "1234567890123456"


def test_collector_process_logs(temp_storage):
    """Test full log processing pipeline."""
    # Create collector with console exporter
    config = ExporterConfig(type="console", min_severity="DEBUG")
    collector = OTelCollector(storage=temp_storage, exporters=[ConsoleExporter(config)])

    # Create OTLP request
    request = logs_service_pb2.ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()

    # Add resource (service name)
    resource_attr = common_pb2.KeyValue()
    resource_attr.key = "service.name"
    resource_attr.value.string_value = "goose"
    resource_logs.resource.attributes.append(resource_attr)

    # Add log record
    scope_logs = resource_logs.scope_logs.add()
    log_record = scope_logs.log_records.add()
    log_record.time_unix_nano = int(time.time() * 1e9)
    log_record.severity_number = 13  # WARN
    log_record.body.string_value = "Warning message"

    # Process
    response = collector.process_logs(request)

    # Check stats
    assert collector.stats["logs_received"] == 1
    assert collector.stats["logs_stored"] == 1
    assert collector.stats["logs_exported"] == 1

    # Check storage
    logs = temp_storage.query(limit=10)
    assert len(logs) == 1
    assert logs[0].service == "goose"
    assert logs[0].severity == "WARN"
    assert logs[0].message == "Warning message"


def test_collector_start_stop(temp_storage):
    """Test collector start/stop."""
    collector = OTelCollector(storage=temp_storage, grpc_port=14317, exporters=[])

    # Start
    collector.start()
    assert collector.running
    time.sleep(0.5)  # Wait for server to start

    # Get stats
    stats = collector.get_stats()
    assert stats["running"]
    assert stats["grpc_port"] == 14317

    # Stop
    collector.stop()
    assert not collector.running


def test_create_default_collector():
    """Test creating default collector."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = create_default_collector(Path(tmpdir) / "otel.db")

        # Should have 4 exporters
        assert len(collector.exporters) == 4

        # Console, file, note, task
        exporter_types = [e.__class__.__name__ for e in collector.exporters]
        assert "ConsoleExporter" in exporter_types
        assert "FileExporter" in exporter_types
        assert "IdlerGearNoteExporter" in exporter_types
        assert "IdlerGearTaskExporter" in exporter_types


def test_grpc_integration(temp_storage):
    """Test full gRPC integration."""
    # Start collector
    collector = OTelCollector(storage=temp_storage, grpc_port=14318, exporters=[])
    collector.start()
    time.sleep(0.5)  # Wait for server to start

    try:
        # Create gRPC client
        channel = grpc.insecure_channel("localhost:14318")
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)

        # Create request
        request = logs_service_pb2.ExportLogsServiceRequest()
        resource_logs = request.resource_logs.add()

        # Add service name
        attr = common_pb2.KeyValue()
        attr.key = "service.name"
        attr.value.string_value = "integration_test"
        resource_logs.resource.attributes.append(attr)

        # Add log
        scope_logs = resource_logs.scope_logs.add()
        log_record = scope_logs.log_records.add()
        log_record.time_unix_nano = int(time.time() * 1e9)
        log_record.severity_number = 17  # ERROR
        log_record.body.string_value = "Integration test error"

        # Send
        response = stub.Export(request)

        # Wait for processing
        time.sleep(0.5)

        # Check storage
        logs = temp_storage.query(limit=10)
        assert len(logs) == 1
        assert logs[0].service == "integration_test"
        assert logs[0].message == "Integration test error"

    finally:
        collector.stop()
