"""OpenTelemetry CLI commands."""

import json
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from idlergear.otel_collector import create_default_collector
from idlergear.otel_storage import OTelStorage

console = Console()

# Global collector instance (for daemon)
_collector = None
_collector_pid_file = Path.home() / ".idlergear" / "otel.pid"


def otel_start(
    grpc_port: int = typer.Option(4317, help="gRPC port for OTLP receiver"),
    http_port: int = typer.Option(4318, help="HTTP port for OTLP receiver"),
    daemon: bool = typer.Option(False, help="Run in background as daemon"),
):
    """Start OpenTelemetry collector."""
    global _collector

    # Check if already running
    if _collector_pid_file.exists():
        try:
            pid = int(_collector_pid_file.read_text().strip())
            # Check if process is alive
            import os

            os.kill(pid, 0)  # Raises error if not alive
            console.print(f"[yellow]Collector already running (PID: {pid})[/yellow]")
            console.print("Use 'idlergear otel stop' to stop it first")
            raise typer.Exit(1)
        except (ProcessLookupError, OSError):
            # Process doesn't exist, clean up stale PID file
            _collector_pid_file.unlink()

    # Create collector
    console.print("[cyan]Starting OpenTelemetry collector...[/cyan]")
    console.print(f"  gRPC: localhost:{grpc_port}")
    console.print(f"  HTTP: localhost:{http_port}")

    _collector = create_default_collector()
    _collector.grpc_port = grpc_port
    _collector.http_port = http_port
    _collector.start()

    # Write PID file
    import os

    _collector_pid_file.parent.mkdir(parents=True, exist_ok=True)
    _collector_pid_file.write_text(str(os.getpid()))

    if daemon:
        console.print("[green]Collector started in daemon mode[/green]")
        console.print(f"PID: {os.getpid()}")

        # Detach from terminal
        sys.stdout.flush()
        sys.stderr.flush()

        # Keep running
        def signal_handler(sig, frame):
            console.print("\n[yellow]Stopping collector...[/yellow]")
            if _collector:
                _collector.stop()
            _collector_pid_file.unlink(missing_ok=True)
            raise typer.Exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Block forever
        signal.pause()
    else:
        console.print("[green]Collector started (press Ctrl+C to stop)[/green]")

        # Register signal handlers
        def signal_handler(sig, frame):
            console.print("\n[yellow]Stopping collector...[/yellow]")
            if _collector:
                _collector.stop()
            _collector_pid_file.unlink(missing_ok=True)
            raise typer.Exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Block until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def otel_stop():
    """Stop OpenTelemetry collector."""
    if not _collector_pid_file.exists():
        console.print("[yellow]Collector is not running[/yellow]")
        raise typer.Exit(1)

    try:
        pid = int(_collector_pid_file.read_text().strip())
        console.print(f"[cyan]Stopping collector (PID: {pid})...[/cyan]")

        # Send SIGTERM
        import os

        os.kill(pid, signal.SIGTERM)

        # Wait for process to die
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except (ProcessLookupError, OSError):
                break

        # Clean up PID file
        _collector_pid_file.unlink(missing_ok=True)
        console.print("[green]Collector stopped[/green]")
    except (ProcessLookupError, OSError) as e:
        console.print(f"[red]Failed to stop collector: {e}[/red]")
        _collector_pid_file.unlink(missing_ok=True)
        raise typer.Exit(1)


def otel_status():
    """Show OpenTelemetry collector status."""
    if not _collector_pid_file.exists():
        console.print("[yellow]Collector is not running[/yellow]")
        raise typer.Exit(1)

    try:
        pid = int(_collector_pid_file.read_text().strip())
        import os

        os.kill(pid, 0)  # Check if alive

        console.print("[green]Collector is running[/green]")
        console.print(f"PID: {pid}")

        # Try to get stats (requires shared state mechanism - for now just show basic info)
        storage = OTelStorage()
        total_logs = storage.count()

        console.print("\n[cyan]Storage Statistics:[/cyan]")
        console.print(f"Total logs: {total_logs:,}")

    except (ProcessLookupError, OSError):
        console.print("[red]Collector PID file exists but process is not running[/red]")
        _collector_pid_file.unlink()
        raise typer.Exit(1)


def otel_logs(
    tail: int = typer.Option(20, help="Show last N logs"),
    service: Optional[str] = typer.Option(None, help="Filter by service name"),
    severity: Optional[str] = typer.Option(
        None, help="Filter by severity (DEBUG, INFO, WARN, ERROR, FATAL)"
    ),
    search: Optional[str] = typer.Option(None, help="Full-text search in messages"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Query and display collected logs."""
    storage = OTelStorage()

    # Build query
    if search:
        logs = storage.search(query=search, limit=tail)
    else:
        logs = storage.query(
            service=service,
            severity=severity,
            limit=tail,
        )

    if not logs:
        console.print("[yellow]No logs found[/yellow]")
        return

    if json_output:
        # Output as JSON
        output = [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "severity": log.severity,
                "service": log.service,
                "message": log.message,
                "attributes": log.attributes,
                "trace_id": log.trace_id,
                "span_id": log.span_id,
            }
            for log in logs
        ]
        print(json.dumps(output, indent=2))
    else:
        # Display as table
        table = Table(title=f"Logs (latest {len(logs)})")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Severity", style="bold")
        table.add_column("Service", style="green")
        table.add_column("Message", style="white")

        for log in logs:
            # Format timestamp
            from datetime import datetime

            dt = datetime.fromtimestamp(log.timestamp / 1e9)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

            # Color code severity
            severity_colors = {
                "DEBUG": "dim",
                "INFO": "white",
                "WARN": "yellow",
                "ERROR": "red",
                "FATAL": "bold red",
            }
            severity_color = severity_colors.get(log.severity, "white")

            table.add_row(
                timestamp_str,
                f"[{severity_color}]{log.severity}[/{severity_color}]",
                log.service,
                log.message[:80] + ("..." if len(log.message) > 80 else ""),
            )

        console.print(table)


def otel_config_show():
    """Show OpenTelemetry configuration."""
    console.print("[cyan]OpenTelemetry Configuration:[/cyan]\n")

    config = {
        "grpc_port": 4317,
        "http_port": 4318,
        "storage_path": str(Path.home() / ".idlergear" / "otel.db"),
        "pid_file": str(_collector_pid_file),
        "exporters": [
            {"type": "console", "enabled": True, "min_severity": "INFO"},
            {
                "type": "file",
                "enabled": True,
                "min_severity": "DEBUG",
                "path": "logs/otel.jsonl",
            },
            {"type": "idlergear_note", "enabled": True, "min_severity": "ERROR"},
            {"type": "idlergear_task", "enabled": True, "min_severity": "FATAL"},
        ],
    }

    console.print(json.dumps(config, indent=2))
    console.print(
        "\n[dim]Note: Configuration is currently hard-coded. YAML config support coming soon![/dim]"
    )
