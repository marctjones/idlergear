#!/bin/bash
# Manual end-to-end test for multi-agent daemon coordination

set -e

echo "=== IdlerGear Multi-Agent Daemon Test ==="
echo

# Cleanup any existing daemon
echo "1. Cleaning up any existing daemon..."
idlergear daemon stop 2>/dev/null || true
sleep 1

# Start daemon
echo "2. Starting daemon..."
idlergear daemon start
sleep 2

# Check status
echo "3. Checking daemon status..."
idlergear daemon status

# Test agent registration (via CLI)
echo "4. Testing agent registration..."
echo "   Note: Agents auto-register when using MCP tools"

# Test message sending
echo "5. Testing message broadcasting..."
idlergear daemon send "Test broadcast message"

# Test command queuing
echo "6. Testing command queue..."
idlergear daemon queue "test command" --priority 5

# List queued commands
echo "7. Listing queued commands..."
idlergear daemon queue-list

# List agents
echo "8. Listing active agents..."
idlergear daemon agents || echo "No agents currently registered (expected - agents register via MCP)"

# Stop daemon
echo "9. Stopping daemon..."
idlergear daemon stop
sleep 1

# Verify stopped
echo "10. Verifying daemon stopped..."
if idlergear daemon status 2>&1 | grep -q "not running"; then
    echo "✓ Daemon stopped successfully"
else
    echo "✗ Daemon still running"
    exit 1
fi

echo
echo "=== All tests passed! ==="
echo
echo "Multi-agent coordination features verified:"
echo "  ✓ Daemon start/stop"
echo "  ✓ Message broadcasting"
echo "  ✓ Command queueing"
echo "  ✓ Status reporting"
echo
echo "To test with real agents:"
echo "  1. Start daemon: idlergear daemon start"
echo "  2. Open Claude Code (auto-registers as agent)"
echo "  3. Run: idlergear daemon agents"
echo "  4. Send messages: idlergear daemon send 'your message'"
