#!/bin/bash
# Demo: Verify MCP Server Integration
#
# This script verifies that the IdlerGear MCP server is properly configured
# and can be discovered by Claude Code.
#
# Unlike the WarGames demo which tests Claude usage, this script focuses on
# the technical integration: does MCP work correctly?
#
# Usage:
#   ./demo-mcp-verification.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Add bin/ to PATH for wrapper scripts
export PATH="$SCRIPT_DIR/bin:$PATH"

echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}              ${BOLD}IdlerGear MCP Server Verification${NC}                        ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

check_result() {
    local test_name="$1"
    local condition="$2"

    if eval "$condition"; then
        echo -e "  ${GREEN}✓${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗${NC} $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Create temp directory
DEMO_DIR=$(mktemp -d -t idlergear-mcp-demo-XXXXXX)
cd "$DEMO_DIR"

cleanup() {
    rm -rf "$DEMO_DIR"
    echo -e "${DIM}Cleaned up: $DEMO_DIR${NC}"
}
trap cleanup EXIT

echo -e "${YELLOW}━━━ Test 1: Executable Availability ━━━${NC}"
echo

check_result "idlergear CLI is available" "command -v idlergear >/dev/null 2>&1"
check_result "idlergear-mcp is available" "command -v idlergear-mcp >/dev/null 2>&1"

echo
echo -e "${YELLOW}━━━ Test 2: Initialize Project ━━━${NC}"
echo

idlergear init >/dev/null

check_result ".idlergear directory created" "[ -d .idlergear ]"
check_result "config.toml created" "[ -f .idlergear/config.toml ]"
check_result "vision.md created" "[ -f .idlergear/vision.md ]"

echo
echo -e "${YELLOW}━━━ Test 3: Install Integration ━━━${NC}"
echo

idlergear install >/dev/null

check_result "CLAUDE.md created" "[ -f CLAUDE.md ]"
check_result "AGENTS.md created" "[ -f AGENTS.md ]"
check_result ".mcp.json created" "[ -f .mcp.json ]"
check_result ".claude/rules/idlergear.md created" "[ -f .claude/rules/idlergear.md ]"

echo
echo -e "${YELLOW}━━━ Test 4: MCP Configuration ━━━${NC}"
echo

# Check .mcp.json structure
MCP_COMMAND=$(python3 -c "import json; print(json.load(open('.mcp.json'))['mcpServers']['idlergear']['command'])" 2>/dev/null || echo "")
MCP_TYPE=$(python3 -c "import json; print(json.load(open('.mcp.json'))['mcpServers']['idlergear']['type'])" 2>/dev/null || echo "")

check_result "MCP command is idlergear-mcp" "[ '$MCP_COMMAND' = 'idlergear-mcp' ]"
check_result "MCP type is stdio" "[ '$MCP_TYPE' = 'stdio' ]"

echo
echo -e "${YELLOW}━━━ Test 5: MCP Server Startup ━━━${NC}"
echo

# Test that MCP server can start and respond to initialize
INIT_MSG='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Send init message and capture output (with timeout)
MCP_OUTPUT=$(echo "$INIT_MSG" | timeout 5 idlergear-mcp 2>&1 || true)

check_result "MCP server starts without crashing" "[ -n '$MCP_OUTPUT' ]"
check_result "MCP server returns JSON-RPC response" "echo '$MCP_OUTPUT' | grep -q 'jsonrpc'"

echo
echo -e "${YELLOW}━━━ Test 6: CLAUDE.md Content ━━━${NC}"
echo

CLAUDE_CONTENT=$(cat CLAUDE.md)

check_result "CLAUDE.md mentions idlergear" "echo '$CLAUDE_CONTENT' | grep -qi 'idlergear'"
check_result "CLAUDE.md mentions context command" "echo '$CLAUDE_CONTENT' | grep -qi 'context'"
check_result "CLAUDE.md mentions FORBIDDEN patterns" "echo '$CLAUDE_CONTENT' | grep -q 'FORBIDDEN'"

echo
echo -e "${YELLOW}━━━ Test 7: AGENTS.md Content ━━━${NC}"
echo

AGENTS_CONTENT=$(cat AGENTS.md)

check_result "AGENTS.md mentions IdlerGear" "echo '$AGENTS_CONTENT' | grep -q 'IdlerGear'"
check_result "AGENTS.md mentions task create" "echo '$AGENTS_CONTENT' | grep -q 'task create'"
check_result "AGENTS.md mentions note create" "echo '$AGENTS_CONTENT' | grep -q 'note create'"
check_result "AGENTS.md mentions FORBIDDEN files" "echo '$AGENTS_CONTENT' | grep -q 'TODO.md'"

echo
echo -e "${YELLOW}━━━ Test 8: Rules File Content ━━━${NC}"
echo

RULES_CONTENT=$(cat .claude/rules/idlergear.md)

check_result "Rules file has alwaysApply: true" "echo '$RULES_CONTENT' | grep -q 'alwaysApply: true'"
check_result "Rules file mentions session start" "echo '$RULES_CONTENT' | grep -qi 'session'"
check_result "Rules file mentions forbidden files" "echo '$RULES_CONTENT' | grep -q 'TODO.md'"

echo
echo -e "${YELLOW}━━━ Test 9: CLI Commands Work ━━━${NC}"
echo

# Test core commands work
idlergear task create "Test task" >/dev/null 2>&1
check_result "task create works" "idlergear task list 2>/dev/null | grep -q 'Test task'"

idlergear note create "Test note" >/dev/null 2>&1
check_result "note create works" "idlergear note list 2>/dev/null | grep -q 'Test note'"

check_result "context command works" "idlergear context >/dev/null 2>&1"

echo
echo -e "${YELLOW}━━━ Test 10: Context Output ━━━${NC}"
echo

CONTEXT_OUTPUT=$(idlergear context 2>/dev/null)

check_result "Context shows vision section" "echo '$CONTEXT_OUTPUT' | grep -q 'Vision'"
check_result "Context shows tasks section" "echo '$CONTEXT_OUTPUT' | grep -q 'Task'"
check_result "Context shows our test task" "echo '$CONTEXT_OUTPUT' | grep -q 'Test task'"

echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                          ${BOLD}RESULTS${NC}                                       ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  Tests passed: ${GREEN}${BOLD}$TESTS_PASSED${NC}"
echo -e "  Tests failed: ${RED}${BOLD}$TESTS_FAILED${NC}"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  ✓ All MCP integration tests passed!${NC}"
    echo
    echo "  The IdlerGear MCP server is properly configured for Claude Code."
    echo "  When Claude Code starts in a project with these files, it should:"
    echo "    • Load the IdlerGear MCP server"
    echo "    • Have access to IdlerGear tools (task_create, note_create, etc.)"
    echo "    • Follow the rules in CLAUDE.md and .claude/rules/"
    exit 0
else
    echo -e "${RED}  Some tests failed. Check the output above.${NC}"
    exit 1
fi
