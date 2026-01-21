---
id: 48
title: Add OpenTelemetry collector for log collection
state: closed
created: '2026-01-07T03:08:00.072956Z'
labels:
- enhancement
- opentelemetry
- logging
- observability
priority: high
---
Implement OpenTelemetry (OTel) collector support in IdlerGear to collect logs over the OTel protocol.

## Requirements

### Core Features
1. **OTel Log Collection** - Accept logs via OTLP (OpenTelemetry Protocol)
2. **Multiple Exporters** - Console, file, IdlerGear notes/tasks
3. **Structured Logging** - Parse and structure log data
4. **Trace Context** - Support trace/span context propagation
5. **Configuration** - Flexible YAML/JSON config for collectors/exporters

### Integration Points
- **IdlerGear Notes** - Auto-create notes from error logs
- **IdlerGear Tasks** - Auto-create tasks from critical errors
- **MCP Server** - Expose OTel data via MCP tools
- **CLI** - `idlergear otel start/stop/status/logs`

### Use Cases
1. Collect logs from Goose/Claude Code sessions
2. Track AI assistant interactions and decisions
3. Debug IdlerGear operations
4. Monitor long-running processes
5. Correlate logs with tasks/commits

## Implementation Plan

### Phase 1: Core OTel Collector
- [ ] Install `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`
- [ ] Create `src/idlergear/otel.py` - Collector implementation
- [ ] OTLP receiver (gRPC and HTTP)
- [ ] Log processing pipeline
- [ ] Basic console exporter

### Phase 2: IdlerGear Exporters
- [ ] Create `src/idlergear/otel_exporters.py`
- [ ] NoteExporter - Error logs → notes
- [ ] TaskExporter - Critical errors → tasks
- [ ] FileExporter - Structured JSON/JSONL output
- [ ] FilteringExporter - Rule-based routing

### Phase 3: CLI Integration
- [ ] `idlergear otel start` - Start collector daemon
- [ ] `idlergear otel stop` - Stop collector
- [ ] `idlergear otel status` - Show collector status
- [ ] `idlergear otel logs` - View collected logs
- [ ] `idlergear otel config` - Show/edit configuration

### Phase 4: MCP Tools
- [ ] `idlergear_otel_logs()` - Query collected logs
- [ ] `idlergear_otel_stats()` - Collector statistics
- [ ] `idlergear_otel_export()` - Export logs to various formats

### Phase 5: Configuration
- [ ] Create `.idlergear/otel-config.yaml` template
- [ ] Support environment variables
- [ ] Hot-reload configuration

## Example Configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
      http:
        endpoint: "0.0.0.0:4318"

processors:
  batch:
    timeout: 10s
    send_batch_size: 100

exporters:
  console:
    enabled: true
  
  idlergear_note:
    enabled: true
    min_severity: ERROR
    tags: ["error", "otel"]
  
  idlergear_task:
    enabled: true
    min_severity: FATAL
    labels: ["bug", "automated"]
  
  file:
    path: ".idlergear/logs/otel.jsonl"
    rotation: "daily"

service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [console, idlergear_note, idlergear_task, file]
```

## Example Usage

```bash
# Start OTel collector
idlergear otel start

# Configure Goose to send logs
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
export OTEL_SERVICE_NAME="goose-session"

# View collected logs
idlergear otel logs --tail 50 --severity ERROR

# Query via MCP
idlergear_otel_logs(severity="ERROR", service="goose-session", limit=20)
```

## Benefits

1. **Automatic Error Capture** - AI errors become tasks automatically
2. **Session Insights** - Understand AI decision-making process
3. **Debugging** - Trace issues across multiple tools
4. **Standards-Based** - Use existing OTel tooling ecosystem
5. **Vendor-Neutral** - Works with any OTel-compatible tool

## Dependencies

- `opentelemetry-api` - Core OTel API
- `opentelemetry-sdk` - SDK implementation
- `opentelemetry-exporter-otlp` - OTLP exporter
- `opentelemetry-exporter-otlp-proto-grpc` - gRPC support
- `pyyaml` - Configuration parsing (already have)

## Testing

- Unit tests for exporters
- Integration tests with OTel SDK
- End-to-end tests with real log data
- Performance tests (throughput, latency)

## Estimated Effort

- **Phase 1**: 4-6 hours (core collector)
- **Phase 2**: 3-4 hours (exporters)
- **Phase 3**: 2-3 hours (CLI)
- **Phase 4**: 2-3 hours (MCP)
- **Phase 5**: 1-2 hours (config)
- **Testing**: 3-4 hours

**Total**: 15-22 hours
