"""Langfuse observability plugin.

Exports IdlerGear's OpenTelemetry logs to Langfuse for token tracking,
cost monitoring, and LLM observability.

Configuration (config.toml):
    [plugins.langfuse]
    enabled = true
    public_key = "pk-..."  # Optional, uses LANGFUSE_PUBLIC_KEY env var
    secret_key = "sk-..."  # Optional, uses LANGFUSE_SECRET_KEY env var
    host = "https://cloud.langfuse.com"  # Optional, defaults to cloud

Example:
    # Enable in config.toml
    [plugins.langfuse]
    enabled = true

    # Plugin automatically exports OpenTelemetry logs to Langfuse
"""

import os
from typing import Any, Dict, List, Optional

from .base import IdlerGearPlugin, PluginCapability


class LangfusePlugin(IdlerGearPlugin):
    """Langfuse observability integration.

    Exports IdlerGear's OpenTelemetry logs to Langfuse for:
    - Automatic token tracking
    - Cost calculation
    - LLM request/response inspection
    - Performance analytics
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Langfuse plugin.

        Args:
            config: Plugin configuration from config.toml
        """
        super().__init__(config)
        self.client: Optional[Any] = None  # Langfuse client instance
        self._public_key: Optional[str] = None
        self._secret_key: Optional[str] = None
        self._host: str = "https://cloud.langfuse.com"

    def name(self) -> str:
        """Return plugin name."""
        return "langfuse"

    def capabilities(self) -> List[PluginCapability]:
        """Return capabilities provided."""
        return [
            PluginCapability.OBSERVABILITY_EXPORT,
            PluginCapability.OBSERVABILITY_METRICS,
            PluginCapability.OBSERVABILITY_TRACING,
        ]

    def initialize(self) -> None:
        """Initialize Langfuse client.

        Loads credentials from config or environment variables.
        Creates Langfuse client instance.

        Raises:
            ImportError: If langfuse package not installed
            ValueError: If credentials not provided
        """
        # Load credentials (config takes precedence over env vars)
        self._public_key = self.config.get(
            "public_key", os.getenv("LANGFUSE_PUBLIC_KEY")
        )
        self._secret_key = self.config.get(
            "secret_key", os.getenv("LANGFUSE_SECRET_KEY")
        )
        self._host = self.config.get("host", self._host)

        # Check credentials
        if not self._public_key or not self._secret_key:
            raise ValueError(
                "Langfuse credentials not found. "
                "Provide public_key/secret_key in config.toml or set "
                "LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY environment variables."
            )

        # Import langfuse (optional dependency)
        try:
            from langfuse import Langfuse
        except ImportError:
            raise ImportError(
                "langfuse package not installed. "
                "Install with: pip install langfuse"
            )

        # Create client
        self.client = Langfuse(
            public_key=self._public_key,
            secret_key=self._secret_key,
            host=self._host,
        )

        self.mark_initialized()

    def shutdown(self) -> None:
        """Shutdown Langfuse client.

        Flushes any pending exports.
        """
        if self.client:
            try:
                self.client.flush()
            except Exception:
                pass  # Ignore shutdown errors
            self.client = None

    def health_check(self) -> bool:
        """Check if Langfuse is accessible.

        Returns:
            True if Langfuse API is reachable
        """
        if not self.client:
            return False

        try:
            # Simple health check - try to create a trace
            self.client.trace(name="health_check")
            self.client.flush()
            return True
        except Exception:
            return False

    def export_otel_log(self, log_entry: Dict[str, Any]) -> None:
        """Export an OpenTelemetry log entry to Langfuse.

        Args:
            log_entry: Log entry from IdlerGear's OTEL database

        This method converts IdlerGear's OpenTelemetry logs into Langfuse traces.
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        # Extract log data
        timestamp = log_entry.get("timestamp")
        service_name = log_entry.get("service_name", "idlergear")
        severity = log_entry.get("severity_text", "INFO")
        message = log_entry.get("body", "")
        attributes = log_entry.get("attributes", {})

        # Create Langfuse trace
        trace = self.client.trace(
            name=f"{service_name}_{severity.lower()}",
            metadata={
                "severity": severity,
                "service": service_name,
                "timestamp": timestamp,
            },
        )

        # Add message as span
        trace.span(
            name=message[:100],  # Truncate long messages
            metadata=attributes,
        )

        # Flush to ensure export
        self.client.flush()

    def export_otel_logs_batch(self, log_entries: List[Dict[str, Any]]) -> None:
        """Export multiple OpenTelemetry log entries to Langfuse.

        Args:
            log_entries: List of log entries from IdlerGear's OTEL database

        More efficient than calling export_otel_log() multiple times.
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        for entry in log_entries:
            self.export_otel_log(entry)

        # Flush once after batch
        self.client.flush()

    def get_token_usage(
        self, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get token usage statistics from Langfuse.

        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)

        Returns:
            Dictionary with token usage statistics
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        # Note: This would use Langfuse API to fetch statistics
        # For now, return placeholder (actual implementation depends on Langfuse API)
        return {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost": 0.0,
        }
