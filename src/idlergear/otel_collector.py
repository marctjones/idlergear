"""OpenTelemetry log collector with OTLP receivers and IdlerGear exporters."""

import json
import logging
import threading
from concurrent import futures
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import grpc
from opentelemetry.proto.collector.logs.v1 import (
    logs_service_pb2,
    logs_service_pb2_grpc,
)
from opentelemetry.proto.logs.v1 import logs_pb2

from idlergear.otel_storage import OTelStorage

logger = logging.getLogger(__name__)


@dataclass
class ExporterConfig:
    """Configuration for an exporter."""

    type: str  # console, file, idlergear_note, idlergear_task
    enabled: bool = True
    min_severity: str = "DEBUG"  # DEBUG, INFO, WARN, ERROR, FATAL
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class BaseExporter:
    """Base class for log exporters."""

    def __init__(self, config: ExporterConfig):
        self.config = config
        self.severity_order = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "FATAL": 4}

    def should_export(self, severity: str) -> bool:
        """Check if log should be exported based on severity."""
        log_level = self.severity_order.get(severity, 0)
        min_level = self.severity_order.get(self.config.min_severity, 0)
        return log_level >= min_level

    def export(self, log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Export a log entry. Returns metadata about export (e.g., created task ID)."""
        raise NotImplementedError


class ConsoleExporter(BaseExporter):
    """Export logs to console."""

    def export(self, log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Print log to console."""
        if not self.should_export(log_data["severity"]):
            return None

        timestamp = log_data["timestamp"]
        severity = log_data["severity"]
        service = log_data["service"]
        message = log_data["message"]

        # Format with colors based on severity
        colors = {
            "DEBUG": "\033[90m",  # Gray
            "INFO": "\033[37m",  # White
            "WARN": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "FATAL": "\033[91m",  # Bright red
        }
        reset = "\033[0m"
        color = colors.get(severity, "")

        print(f"{color}[{severity:5s}] {service:15s} | {message}{reset}")
        return None


class FileExporter(BaseExporter):
    """Export logs to file in JSONL format."""

    def __init__(self, config: ExporterConfig):
        super().__init__(config)
        self.file_path = Path(config.config.get("path", "logs/otel.jsonl"))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_handle = None
        self._open_file()

    def _open_file(self):
        """Open log file for appending."""
        self.file_handle = open(self.file_path, "a", encoding="utf-8")

    def export(self, log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Write log to file as JSON line."""
        if not self.should_export(log_data["severity"]):
            return None

        self.file_handle.write(json.dumps(log_data) + "\n")
        self.file_handle.flush()
        return None

    def close(self):
        """Close file handle."""
        if self.file_handle:
            self.file_handle.close()


class IdlerGearNoteExporter(BaseExporter):
    """Export ERROR logs as IdlerGear notes."""

    def export(self, log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create note from error log."""
        if not self.should_export(log_data["severity"]):
            return None

        # Only create notes for ERROR and above
        if self.severity_order[log_data["severity"]] < self.severity_order["ERROR"]:
            return None

        try:
            from idlergear.notes import create_note

            # Format note content
            content = f"""# {log_data["severity"]}: {log_data["message"]}

**Service:** {log_data["service"]}
**Timestamp:** {log_data["timestamp"]}

## Attributes
```json
{json.dumps(log_data.get("attributes", {}), indent=2)}
```

## Trace Context
- Trace ID: {log_data.get("trace_id", "N/A")}
- Span ID: {log_data.get("span_id", "N/A")}
"""

            # Create note with appropriate tags
            tags = ["error", "otel", log_data["service"]]
            if log_data["severity"] == "FATAL":
                tags.append("critical")

            note_id = create_note(content=content, tags=tags)
            logger.info(f"Created note #{note_id} from {log_data['severity']} log")

            return {"created_note_id": note_id}

        except Exception as e:
            logger.error(f"Failed to create note from log: {e}")
            return None


class IdlerGearTaskExporter(BaseExporter):
    """Export FATAL logs as IdlerGear tasks."""

    def export(self, log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create task from fatal error."""
        if not self.should_export(log_data["severity"]):
            return None

        # Only create tasks for FATAL
        if log_data["severity"] != "FATAL":
            return None

        try:
            from idlergear.tasks import create_task

            # Format task
            title = f"[{log_data['service']}] {log_data['message'][:80]}"
            body = f"""# Fatal Error from {log_data["service"]}

**Timestamp:** {log_data["timestamp"]}
**Message:** {log_data["message"]}

## Attributes
```json
{json.dumps(log_data.get("attributes", {}), indent=2)}
```

## Trace Context
- Trace ID: {log_data.get("trace_id", "N/A")}
- Span ID: {log_data.get("span_id", "N/A")}

## Action Required
This fatal error was automatically captured from OpenTelemetry logs. Please investigate and resolve.
"""

            # Create high-priority task
            task_id = create_task(
                title=title,
                body=body,
                priority="high",
                labels=["bug", "automated", "otel"],
            )
            logger.info(f"Created task #{task_id} from FATAL log")

            return {"created_task_id": task_id}

        except Exception as e:
            logger.error(f"Failed to create task from log: {e}")
            return None


class OTelCollector:
    """OpenTelemetry collector with OTLP receivers and multiple exporters."""

    def __init__(
        self,
        storage: OTelStorage,
        grpc_port: int = 4317,
        http_port: int = 4318,
        exporters: Optional[List[ExporterConfig]] = None,
    ):
        self.storage = storage
        self.grpc_port = grpc_port
        self.http_port = http_port

        # Initialize exporters
        self.exporters: List[BaseExporter] = []
        if exporters:
            for exporter in exporters:
                # Handle both ExporterConfig and BaseExporter instances
                if isinstance(exporter, BaseExporter):
                    self.exporters.append(exporter)
                elif isinstance(exporter, ExporterConfig):
                    if not exporter.enabled:
                        continue

                    if exporter.type == "console":
                        self.exporters.append(ConsoleExporter(exporter))
                    elif exporter.type == "file":
                        self.exporters.append(FileExporter(exporter))
                    elif exporter.type == "idlergear_note":
                        self.exporters.append(IdlerGearNoteExporter(exporter))
                    elif exporter.type == "idlergear_task":
                        self.exporters.append(IdlerGearTaskExporter(exporter))
                    else:
                        logger.warning(f"Unknown exporter type: {exporter.type}")
                else:
                    logger.warning(f"Invalid exporter: {exporter}")

        # gRPC server
        self.grpc_server = None
        self.grpc_thread = None

        # HTTP server (for now, just a placeholder)
        self.http_server = None

        # Running state
        self.running = False
        self.stats = {
            "logs_received": 0,
            "logs_stored": 0,
            "logs_exported": 0,
            "errors": 0,
        }

    def _severity_from_number(self, severity_number: int) -> str:
        """Convert OTel severity number to string."""
        if severity_number >= 21:
            return "FATAL"
        elif severity_number >= 17:
            return "ERROR"
        elif severity_number >= 13:
            return "WARN"
        elif severity_number >= 9:
            return "INFO"
        else:
            return "DEBUG"

    def _process_log_record(
        self, log_record: logs_pb2.LogRecord, service_name: str
    ) -> Dict[str, Any]:
        """Process OTel log record into dict."""
        # Extract fields
        timestamp_ns = log_record.time_unix_nano
        severity_number = log_record.severity_number
        severity = self._severity_from_number(severity_number)
        message = (
            log_record.body.string_value
            if log_record.body.HasField("string_value")
            else ""
        )

        # Extract attributes
        attributes = {}
        for attr in log_record.attributes:
            key = attr.key
            if attr.value.HasField("string_value"):
                attributes[key] = attr.value.string_value
            elif attr.value.HasField("int_value"):
                attributes[key] = attr.value.int_value
            elif attr.value.HasField("bool_value"):
                attributes[key] = attr.value.bool_value
            elif attr.value.HasField("double_value"):
                attributes[key] = attr.value.double_value

        # Extract trace context
        trace_id = log_record.trace_id.hex() if log_record.trace_id else None
        span_id = log_record.span_id.hex() if log_record.span_id else None

        return {
            "timestamp": timestamp_ns,
            "severity": severity,
            "service": service_name,
            "message": message,
            "attributes": attributes,
            "trace_id": trace_id,
            "span_id": span_id,
        }

    def _export_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export log to all enabled exporters."""
        metadata = {}

        for exporter in self.exporters:
            try:
                result = exporter.export(log_data)
                self.stats["logs_exported"] += (
                    1  # Count all exports, not just those with metadata
                )
                if result:
                    metadata.update(result)
            except Exception as e:
                logger.error(f"Exporter {exporter.__class__.__name__} failed: {e}")
                self.stats["errors"] += 1

        return metadata

    def process_logs(
        self, request: logs_service_pb2.ExportLogsServiceRequest
    ) -> logs_service_pb2.ExportLogsServiceResponse:
        """Process OTLP logs request."""
        for resource_logs in request.resource_logs:
            # Extract service name from resource
            service_name = "unknown"
            if resource_logs.resource and resource_logs.resource.attributes:
                for attr in resource_logs.resource.attributes:
                    if attr.key == "service.name":
                        service_name = attr.value.string_value
                        break

            # Process each scope logs
            for scope_logs in resource_logs.scope_logs:
                for log_record in scope_logs.log_records:
                    try:
                        self.stats["logs_received"] += 1

                        # Convert to dict
                        log_data = self._process_log_record(log_record, service_name)

                        # Export to exporters (get metadata like created_task_id)
                        metadata = self._export_log(log_data)

                        # Store in database
                        from idlergear.otel_storage import LogEntry

                        entry = LogEntry(
                            timestamp=log_data["timestamp"],
                            severity=log_data["severity"],
                            service=log_data["service"],
                            message=log_data["message"],
                            attributes=log_data["attributes"],
                            trace_id=log_data["trace_id"],
                            span_id=log_data["span_id"],
                            created_task_id=metadata.get("created_task_id"),
                            created_note_id=metadata.get("created_note_id"),
                        )
                        self.storage.insert(entry)
                        self.stats["logs_stored"] += 1

                    except Exception as e:
                        logger.error(f"Failed to process log record: {e}")
                        self.stats["errors"] += 1

        return logs_service_pb2.ExportLogsServiceResponse()

    def start(self):
        """Start the collector (gRPC and HTTP receivers)."""
        if self.running:
            logger.warning("Collector already running")
            return

        self.running = True

        # Start gRPC server
        self._start_grpc_server()

        logger.info(
            f"OTel collector started - gRPC: {self.grpc_port}, HTTP: {self.http_port}"
        )

    def _start_grpc_server(self):
        """Start gRPC server in background thread."""

        class LogsServiceServicer(logs_service_pb2_grpc.LogsServiceServicer):
            def __init__(self, collector):
                self.collector = collector

            def Export(self, request, context):
                return self.collector.process_logs(request)

        # Create and start gRPC server
        self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        logs_service_pb2_grpc.add_LogsServiceServicer_to_server(
            LogsServiceServicer(self), self.grpc_server
        )
        self.grpc_server.add_insecure_port(f"[::]:{self.grpc_port}")

        def run_server():
            self.grpc_server.start()
            logger.info(f"gRPC server listening on port {self.grpc_port}")
            self.grpc_server.wait_for_termination()

        self.grpc_thread = threading.Thread(target=run_server, daemon=True)
        self.grpc_thread.start()

    def stop(self):
        """Stop the collector."""
        if not self.running:
            logger.warning("Collector not running")
            return

        self.running = False

        # Stop gRPC server
        if self.grpc_server:
            self.grpc_server.stop(grace=5)

        # Close file exporters
        for exporter in self.exporters:
            if isinstance(exporter, FileExporter):
                exporter.close()

        logger.info("OTel collector stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            "running": self.running,
            "grpc_port": self.grpc_port,
            "http_port": self.http_port,
            "stats": self.stats,
            "exporters": [
                {
                    "type": e.__class__.__name__,
                    "enabled": e.config.enabled,
                    "min_severity": e.config.min_severity,
                }
                for e in self.exporters
            ],
        }


def create_default_collector(storage_path: Optional[Path] = None) -> OTelCollector:
    """Create collector with default configuration."""
    # Create storage
    storage = OTelStorage(storage_path)

    # Default exporters
    exporters = [
        ExporterConfig(type="console", enabled=True, min_severity="INFO"),
        ExporterConfig(
            type="file",
            enabled=True,
            min_severity="DEBUG",
            config={"path": "logs/otel.jsonl"},
        ),
        ExporterConfig(type="idlergear_note", enabled=True, min_severity="ERROR"),
        ExporterConfig(type="idlergear_task", enabled=True, min_severity="FATAL"),
    ]

    return OTelCollector(storage=storage, exporters=exporters)
