#!/bin/bash
# Multi-Agent Coordination Demo
# This script demonstrates how multiple AI assistants can coordinate through IdlerGear

set -e

echo "=========================================="
echo "IdlerGear Multi-Agent Coordination Demo"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

step() {
    echo -e "${BLUE}[Step $1]${NC} $2"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Step 1: Start the daemon
step 1 "Starting IdlerGear daemon..."
python3 -m idlergear.cli daemon start || true
sleep 1
success "Daemon started"
echo ""

# Step 2: Show daemon status
step 2 "Checking daemon status..."
python3 -m idlergear.cli daemon status
echo ""

# Step 3: Queue some commands
step 3 "Queueing commands for AI agents..."
CMD1=$(python3 -m idlergear.cli daemon queue "Implement user authentication" --priority 10)
CMD2=$(python3 -m idlergear.cli daemon queue "Write unit tests" --priority 5)
CMD3=$(python3 -m idlergear.cli daemon queue "Update documentation" --priority 3)
success "Queued 3 commands"
echo ""

# Step 4: List queued commands
step 4 "Listing queued commands..."
python3 -m idlergear.cli daemon queue-list
echo ""

# Step 5: Simulate agent registration
step 5 "Simulating AI agent connections..."
info "In a real scenario, agents register automatically via MCP"
info "For demo purposes, we'll show how they would appear:"
echo ""
echo "  Agent: Claude Code"
echo "  Status: idle"
echo "  Type: claude-code"
echo ""
echo "  Agent: Goose Terminal"
echo "  Status: busy
echo "  Type: goose"
echo ""

# Step 6: List active agents
step 6 "Listing active AI agents..."
python3 -m idlergear.cli daemon agents || info "No agents connected yet (expected in demo)"
echo ""

# Step 7: Send a broadcast message
step 7 "Broadcasting message to all agents..."
python3 -m idlergear.cli daemon send "Database schema updated - review migrations"
success "Message sent to all active agents"
echo ""

# Step 8: Show token-efficient context
step 8 "Retrieving project context (minimal mode)..."
python3 -m idlergear.cli context --mode minimal | head -30
echo "..."
success "Context retrieved (~750 tokens)"
echo ""

# Step 9: Create a task using IdlerGear
step 9 "Creating a task..."
python3 -m idlergear.cli task create "Integrate OAuth 2.0" \
    --label feature \
    --priority high
success "Task created"
echo ""

# Step 10: Show how it all ties together
step 10 "How it all works together:"
echo ""
cat << 'EOF'
┌─────────────────────────────────────────────────────────────┐
│                  IdlerGear Daemon                           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Agent Registry│  │ Command Queue│  │ Lock Manager │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
└──────────┬──────────────────┬─────────────────┬───────────┘
           │                  │                 │
    ┌──────▼───────┐   ┌─────▼──────┐   ┌─────▼──────┐
    │ Claude Code  │   │    Goose   │   │    Aider   │
    │              │   │            │   │            │
    │ Status: busy │   │ Status: idle│   │Status: idle│
    └──────────────┘   └────────────┘   └────────────┘

Features:
  • Queue commands for any available agent
  • Broadcast messages to all agents
  • Track agent status in real-time
  • Coordinate writes with locks
  • Token-efficient context retrieval
EOF
echo ""

# Cleanup
step 11 "Cleanup..."
info "In production, daemon keeps running across sessions"
info "To stop: python3 -m idlergear.cli daemon stop"
echo ""

success "Demo complete!"
echo ""
echo "Next steps:"
echo "  1. Start daemon: python3 -m idlergear.cli daemon start"
echo "  2. Queue work: python3 -m idlergear.cli daemon queue 'your command'"
echo "  3. Check agents: python3 -m idlergear.cli daemon agents"
echo "  4. Get context: python3 -m idlergear.cli context --mode minimal"
echo ""
