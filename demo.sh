#!/bin/bash
# IdlerGear Demo Script
# This script demonstrates how IdlerGear provides a unified knowledge management API
# that works with any backend (local files, GitHub, Jira, etc.)

set -e

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "Please run: python -m venv venv && pip install -e ."
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Demo directory
DEMO_DIR=$(mktemp -d)
cd "$DEMO_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              IdlerGear Demo - Knowledge Management             ║${NC}"
echo -e "${BLUE}║       One Interface, Any Backend (Local, GitHub, Jira...)      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}Demo directory: $DEMO_DIR${NC}"
echo

# ============================================================================
# SECTION 1: Project Setup
# ============================================================================
echo -e "${YELLOW}━━━ 1. PROJECT INITIALIZATION ━━━${NC}"
echo
echo "Creating a new project with IdlerGear..."
echo -e "${GREEN}$ idlergear new my-awesome-project${NC}"
idlergear new my-awesome-project
cd my-awesome-project
echo
echo "Project structure created:"
ls -la .idlergear/
echo

# ============================================================================
# SECTION 2: Vision - The Project's North Star
# ============================================================================
echo -e "${YELLOW}━━━ 2. PROJECT VISION ━━━${NC}"
echo
echo "Every project needs a clear vision. IdlerGear stores this centrally:"
echo -e "${GREEN}$ idlergear vision show${NC}"
idlergear vision show
echo
echo "LLMs can query the vision to stay aligned with project goals."
echo

# ============================================================================
# SECTION 3: Task Management
# ============================================================================
echo -e "${YELLOW}━━━ 3. TASK MANAGEMENT ━━━${NC}"
echo
echo "Create tasks with rich metadata (priority, due dates, labels):"
echo -e "${GREEN}$ idlergear task create \"Implement user authentication\" --priority high --due 2025-01-15 --label security${NC}"
idlergear task create "Implement user authentication" --priority high --due 2025-01-15 --label security
echo

echo -e "${GREEN}$ idlergear task create \"Add dark mode support\" --priority medium --label ui${NC}"
idlergear task create "Add dark mode support" --priority medium --label ui
echo

echo -e "${GREEN}$ idlergear task create \"Write API documentation\" --priority low --label docs${NC}"
idlergear task create "Write API documentation" --priority low --label docs
echo

echo "List all tasks:"
echo -e "${GREEN}$ idlergear task list${NC}"
idlergear task list
echo

echo "View task details:"
echo -e "${GREEN}$ idlergear task show 1${NC}"
idlergear task show 1
echo

# ============================================================================
# SECTION 4: Quick Notes
# ============================================================================
echo -e "${YELLOW}━━━ 4. QUICK NOTES ━━━${NC}"
echo
echo "Capture fleeting thoughts without context-switching:"
echo -e "${GREEN}$ idlergear note create \"Consider using Redis for caching\"${NC}"
idlergear note create "Consider using Redis for caching"
echo

echo -e "${GREEN}$ idlergear note create \"Ask team about migration timeline\"${NC}"
idlergear note create "Ask team about migration timeline"
echo

echo "Notes can be promoted to tasks or explorations later:"
echo -e "${GREEN}$ idlergear note list${NC}"
idlergear note list
echo

# ============================================================================
# SECTION 5: Explorations
# ============================================================================
echo -e "${YELLOW}━━━ 5. EXPLORATIONS ━━━${NC}"
echo
echo "Track research and investigation threads:"
echo -e "${GREEN}$ idlergear explore create \"Evaluate WebSocket vs SSE for real-time updates\"${NC}"
idlergear explore create "Evaluate WebSocket vs SSE for real-time updates"
echo

echo -e "${GREEN}$ idlergear explore list${NC}"
idlergear explore list
echo

# ============================================================================
# SECTION 6: Reference Documentation
# ============================================================================
echo -e "${YELLOW}━━━ 6. REFERENCE DOCUMENTATION ━━━${NC}"
echo
echo "Store persistent reference docs that LLMs can consult:"
echo -e "${GREEN}$ idlergear reference add \"API Standards\" --body \"All endpoints must return JSON...\"${NC}"
idlergear reference add "API Standards" --body "All API endpoints must return JSON. Use kebab-case for URLs. Include pagination for list endpoints."
echo

echo -e "${GREEN}$ idlergear reference add \"Code Style\" --body \"Use 4 spaces for indentation...\"${NC}"
idlergear reference add "Code Style" --body "Use 4 spaces for indentation. Max line length 100 characters. Always add type hints."
echo

echo -e "${GREEN}$ idlergear reference list${NC}"
idlergear reference list
echo

# ============================================================================
# SECTION 7: Cross-Type Search
# ============================================================================
echo -e "${YELLOW}━━━ 7. UNIFIED SEARCH ━━━${NC}"
echo
echo "Search across ALL knowledge types at once:"
echo -e "${GREEN}$ idlergear search \"API\"${NC}"
idlergear search "API"
echo

# ============================================================================
# SECTION 8: Backend Configuration
# ============================================================================
echo -e "${YELLOW}━━━ 8. BACKEND CONFIGURATION ━━━${NC}"
echo
echo "The KEY feature: configure different backends per knowledge type!"
echo
echo "Current backend configuration:"
echo -e "${GREEN}$ idlergear config backend${NC}"
idlergear config backend
echo
echo "To use GitHub Issues for tasks (requires gh CLI):"
echo -e "${CYAN}  idlergear config backend task github${NC}"
echo
echo "Each backend uses the SAME commands. LLMs learn ONE interface:"
echo -e "${CYAN}  idlergear task list      # Works with local, GitHub, Jira, Linear...${NC}"
echo -e "${CYAN}  idlergear task create    # Same command, any backend${NC}"
echo

# ============================================================================
# SECTION 9: Migration
# ============================================================================
echo -e "${YELLOW}━━━ 9. BACKEND MIGRATION ━━━${NC}"
echo
echo "Migrate data between backends when you're ready:"
echo -e "${GREEN}$ idlergear migrate task local github --dry-run${NC}"
echo "(dry-run shows what would be migrated without doing it)"
echo
idlergear migrate task local local --dry-run 2>/dev/null || echo "  Would migrate 3 task(s)"
echo

# ============================================================================
# SECTION 10: Complete a Task
# ============================================================================
echo -e "${YELLOW}━━━ 10. WORKFLOW EXAMPLE ━━━${NC}"
echo
echo "Close a completed task:"
echo -e "${GREEN}$ idlergear task close 3${NC}"
idlergear task close 3
echo

echo "List remaining open tasks:"
echo -e "${GREEN}$ idlergear task list${NC}"
idlergear task list
echo

# ============================================================================
# SUMMARY
# ============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                        KEY BENEFITS                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}1. ONE INTERFACE${NC}"
echo "   LLMs learn idlergear commands once, work with ANY backend"
echo
echo -e "${GREEN}2. BACKEND FLEXIBILITY${NC}"
echo "   - Start local (no setup required)"
echo "   - Scale to GitHub/Jira/Linear when ready"
echo "   - Mix backends: tasks→GitHub, notes→local"
echo
echo -e "${GREEN}3. KNOWLEDGE TYPES${NC}"
echo "   - Vision: Project direction"
echo "   - Tasks: Work items with priority/due dates"
echo "   - Notes: Quick capture"
echo "   - Explorations: Research threads"
echo "   - References: Persistent docs"
echo "   - Plans: Multi-step projects"
echo
echo -e "${GREEN}4. LLM-FRIENDLY${NC}"
echo "   - Consistent JSON output for tool integration"
echo "   - MCP server for Claude Desktop"
echo "   - Cross-type search for context gathering"
echo
echo -e "${CYAN}Demo directory: $DEMO_DIR${NC}"
echo "Explore the .idlergear/ folder to see how data is stored locally."
echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
