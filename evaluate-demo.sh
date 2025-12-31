#!/bin/bash
# Evaluate IdlerGear Demo Quality
#
# This script evaluates the quality of a demo run by checking:
# 1. Did Claude use IdlerGear appropriately?
# 2. Did Claude avoid forbidden patterns?
# 3. Are the generated games functional?
# 4. Is the tracked knowledge useful?
#
# Usage:
#   ./evaluate-demo.sh /path/to/demo/directory
#
# Returns exit code 0 if evaluation passes, 1 if issues found

set -e

if [ -z "$1" ]; then
    echo "Usage: ./evaluate-demo.sh <demo-directory>"
    echo ""
    echo "Example: ./evaluate-demo.sh /tmp/idlergear-wargames-demo-abc123"
    exit 1
fi

DEMO_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$DEMO_DIR" ]; then
    echo "Error: Directory not found: $DEMO_DIR"
    exit 1
fi

# Add idlergear to PATH
export PATH="$SCRIPT_DIR/bin:$PATH"

cd "$DEMO_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}              ${BOLD}IdlerGear Demo Quality Evaluation${NC}                        ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${DIM}Evaluating: $DEMO_DIR${NC}"
echo

# Scoring
TOTAL_POINTS=0
MAX_POINTS=0
ISSUES=()

score() {
    local points="$1"
    local max="$2"
    local description="$3"

    MAX_POINTS=$((MAX_POINTS + max))
    TOTAL_POINTS=$((TOTAL_POINTS + points))

    if [ "$points" -eq "$max" ]; then
        echo -e "  ${GREEN}✓${NC} $description (${points}/${max})"
    elif [ "$points" -gt 0 ]; then
        echo -e "  ${YELLOW}○${NC} $description (${points}/${max})"
    else
        echo -e "  ${RED}✗${NC} $description (${points}/${max})"
    fi
}

issue() {
    ISSUES+=("$1")
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: IdlerGear Usage
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}━━━ Section 1: IdlerGear Usage ━━━${NC}"
echo

# Check if IdlerGear was initialized
if [ -d .idlergear ]; then
    score 1 1 "IdlerGear initialized"
else
    score 0 1 "IdlerGear initialized"
    issue "IdlerGear was not initialized"
fi

# Count tasks created
TASK_OUTPUT=$(idlergear task list 2>/dev/null || echo "")
TASK_COUNT=$(echo "$TASK_OUTPUT" | grep -c "^  #" || true)
TASK_COUNT=${TASK_COUNT:-0}
if [ "$TASK_COUNT" -ge 3 ]; then
    score 3 3 "Tasks created (${TASK_COUNT} tasks)"
elif [ "$TASK_COUNT" -ge 1 ]; then
    score 1 3 "Tasks created (${TASK_COUNT} tasks - expected 3+)"
    issue "Only ${TASK_COUNT} task(s) created, expected 3+"
else
    score 0 3 "Tasks created (none)"
    issue "No tasks were created"
fi

# Count notes created
NOTE_OUTPUT=$(idlergear note list 2>/dev/null || echo "")
NOTE_COUNT=$(echo "$NOTE_OUTPUT" | grep -c "^  #" || true)
NOTE_COUNT=${NOTE_COUNT:-0}
if [ "$NOTE_COUNT" -ge 3 ]; then
    score 3 3 "Notes created (${NOTE_COUNT} notes)"
elif [ "$NOTE_COUNT" -ge 1 ]; then
    score 1 3 "Notes created (${NOTE_COUNT} notes - expected 3+)"
    issue "Only ${NOTE_COUNT} note(s) created, expected 3+"
else
    score 0 3 "Notes created (none)"
    issue "No notes were created"
fi

# Check if vision was set
VISION=$(idlergear vision show 2>/dev/null || echo "")
if [ -n "$VISION" ] && [ "$VISION" != "# Project Vision" ]; then
    score 2 2 "Project vision set"
else
    score 0 2 "Project vision set"
    issue "Project vision was not set"
fi

# Check context output
CONTEXT=$(idlergear context 2>/dev/null || echo "")
if echo "$CONTEXT" | grep -qi "task"; then
    score 1 1 "Context command shows tasks"
else
    score 0 1 "Context command shows tasks"
fi

echo

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Forbidden Patterns
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}━━━ Section 2: Forbidden Patterns ━━━${NC}"
echo

# Check for forbidden files
FORBIDDEN_FILES=("TODO.md" "TODO.txt" "TASKS.md" "NOTES.md" "SCRATCH.md" "BACKLOG.md")
FORBIDDEN_FOUND=0

for file in "${FORBIDDEN_FILES[@]}"; do
    if [ -f "$file" ]; then
        FORBIDDEN_FOUND=$((FORBIDDEN_FOUND + 1))
        issue "Forbidden file created: $file"
    fi
done

if [ "$FORBIDDEN_FOUND" -eq 0 ]; then
    score 3 3 "No forbidden tracking files created"
else
    score 0 3 "No forbidden tracking files created (found ${FORBIDDEN_FOUND})"
fi

# Check for TODO comments in Python files
TODO_COMMENTS=0
for pyfile in *.py; do
    if [ -f "$pyfile" ]; then
        count=$(grep -c "# TODO:" "$pyfile" 2>/dev/null || true)
        count=${count:-0}
        count=$(echo "$count" | tr -d '[:space:]')
        if [ -n "$count" ] && [ "$count" -gt 0 ] 2>/dev/null; then
            TODO_COMMENTS=$((TODO_COMMENTS + count))
        fi
    fi
done

if [ "$TODO_COMMENTS" -eq 0 ]; then
    score 2 2 "No TODO comments in code"
else
    score 0 2 "No TODO comments in code (found ${TODO_COMMENTS})"
    issue "Found ${TODO_COMMENTS} TODO comments in Python files"
fi

echo

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Code Quality
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}━━━ Section 3: Code Quality ━━━${NC}"
echo

# Check if tictactoe.py exists and is substantial
if [ -f tictactoe.py ]; then
    LINES=$(wc -l < tictactoe.py)
    if [ "$LINES" -ge 50 ]; then
        score 2 2 "tictactoe.py is substantial (${LINES} lines)"
    else
        score 1 2 "tictactoe.py exists but small (${LINES} lines)"
        issue "tictactoe.py is only ${LINES} lines, expected 50+"
    fi

    # Check if it's syntactically valid Python
    if python3 -m py_compile tictactoe.py 2>/dev/null; then
        score 2 2 "tictactoe.py is valid Python"
    else
        score 0 2 "tictactoe.py is valid Python"
        issue "tictactoe.py has syntax errors"
    fi

    # Check for key features
    FEATURES=0
    grep -q "def " tictactoe.py && FEATURES=$((FEATURES + 1))
    grep -qi "win" tictactoe.py && FEATURES=$((FEATURES + 1))
    grep -qi "draw\|tie" tictactoe.py && FEATURES=$((FEATURES + 1))
    grep -qi "board" tictactoe.py && FEATURES=$((FEATURES + 1))

    if [ "$FEATURES" -ge 3 ]; then
        score 2 2 "tictactoe.py has expected features"
    elif [ "$FEATURES" -ge 1 ]; then
        score 1 2 "tictactoe.py has some features (${FEATURES}/4)"
    else
        score 0 2 "tictactoe.py has expected features"
        issue "tictactoe.py missing key game features"
    fi

    # Smoke test: Check for runnable structure
    # We check if the file has main guard and expected functions
    HAS_MAIN_GUARD=$(grep -c "if __name__" tictactoe.py 2>/dev/null || echo 0)
    HAS_FUNCTIONS=$(grep -c "^def " tictactoe.py 2>/dev/null || echo 0)

    if [ "$HAS_MAIN_GUARD" -gt 0 ] && [ "$HAS_FUNCTIONS" -ge 3 ]; then
        # Try to actually run Python syntax check + basic import
        if python3 -c "
import sys
# Redirect stdin to prevent hanging on input()
import io
sys.stdin = io.StringIO('')
# Try importing - will fail on input() but that's ok
try:
    exec(open('tictactoe.py').read().replace('if __name__', 'if False and __name__'))
    print('OK')
except EOFError:
    print('OK')  # Expected - game tried to read input
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1 | grep -q "OK"; then
            score 3 3 "tictactoe.py smoke test (importable, ${HAS_FUNCTIONS} functions)"
        else
            score 2 3 "tictactoe.py smoke test (has structure)"
        fi
    elif [ "$HAS_FUNCTIONS" -ge 2 ]; then
        score 2 3 "tictactoe.py smoke test (${HAS_FUNCTIONS} functions, no main guard)"
    else
        score 1 3 "tictactoe.py smoke test (minimal structure)"
        issue "tictactoe.py has minimal structure"
    fi
else
    score 0 9 "tictactoe.py exists and works"
    issue "tictactoe.py was not created"
fi

# Check if poker.py exists
if [ -f poker.py ]; then
    LINES=$(wc -l < poker.py)
    if [ "$LINES" -ge 50 ]; then
        score 2 2 "poker.py is substantial (${LINES} lines)"
    else
        score 1 2 "poker.py exists but small (${LINES} lines)"
    fi

    if python3 -m py_compile poker.py 2>/dev/null; then
        score 2 2 "poker.py is valid Python"
    else
        score 0 2 "poker.py is valid Python"
        issue "poker.py has syntax errors"
    fi

    # Smoke test for poker - simpler structure check
    POKER_MAIN_GUARD=$(grep -c "if __name__" poker.py 2>/dev/null || echo 0)
    POKER_FUNCTIONS=$(grep -c "^def " poker.py 2>/dev/null || echo 0)

    if [ "$POKER_MAIN_GUARD" -gt 0 ] && [ "$POKER_FUNCTIONS" -ge 3 ]; then
        score 2 2 "poker.py smoke test (${POKER_FUNCTIONS} functions, main guard)"
    elif [ "$POKER_FUNCTIONS" -ge 2 ]; then
        score 1 2 "poker.py smoke test (${POKER_FUNCTIONS} functions)"
    else
        score 0 2 "poker.py smoke test"
        issue "poker.py has minimal structure"
    fi
else
    score 0 6 "poker.py created"
    issue "poker.py was not created"
fi

# Check for design documents
DESIGN_DOCS=0
[ -f thermonuclear_war_design.md ] && DESIGN_DOCS=$((DESIGN_DOCS + 1))
[ -f thermonuclear_war.py ] && DESIGN_DOCS=$((DESIGN_DOCS + 1))
[ -f falkens_maze_design.md ] && DESIGN_DOCS=$((DESIGN_DOCS + 1))
[ -f falkens_maze.py ] && DESIGN_DOCS=$((DESIGN_DOCS + 1))

if [ "$DESIGN_DOCS" -ge 2 ]; then
    score 2 2 "Design phase games created (${DESIGN_DOCS} files)"
elif [ "$DESIGN_DOCS" -ge 1 ]; then
    score 1 2 "Design phase games created (${DESIGN_DOCS} files)"
else
    score 0 2 "Design phase games created"
    issue "No design documents or starter files created"
fi

# Check for WOPR main menu (bonus integration challenge)
if [ -f wopr.py ]; then
    WOPR_LINES=$(wc -l < wopr.py)
    if [ "$WOPR_LINES" -ge 50 ]; then
        score 3 3 "wopr.py WOPR menu created (${WOPR_LINES} lines)"
    else
        score 2 3 "wopr.py exists but small (${WOPR_LINES} lines)"
    fi

    # Check if it integrates with other games
    if grep -qi "subprocess\|tictactoe\|poker" wopr.py 2>/dev/null; then
        score 2 2 "WOPR integrates with other games"
    else
        score 1 2 "WOPR integrates with other games (partial)"
    fi
else
    score 0 5 "wopr.py WOPR menu created"
    issue "WOPR main menu was not created"
fi

echo

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Knowledge Quality
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}━━━ Section 4: Knowledge Quality ━━━${NC}"
echo

# Check if tasks are meaningful (not just "Task 1", "Task 2")
# Reuse TASK_OUTPUT from earlier
MEANINGFUL_TASKS=0

if echo "$TASK_OUTPUT" | grep -qi "tic-tac-toe\|tictactoe\|game\|implement\|build\|create\|poker\|maze\|war"; then
    MEANINGFUL_TASKS=1
fi

if [ "$MEANINGFUL_TASKS" -eq 1 ]; then
    score 2 2 "Tasks have meaningful descriptions"
elif [ "$TASK_COUNT" -gt 0 ]; then
    score 1 2 "Tasks have meaningful descriptions"
    issue "Task descriptions may be generic"
else
    score 0 2 "Tasks have meaningful descriptions"
fi

# Check if notes contain useful information
# Reuse NOTE_OUTPUT from earlier
MEANINGFUL_NOTES=0

if echo "$NOTE_OUTPUT" | grep -qiE "design|decision|approach|algorithm|feature|implemented|completed|using|style|aesthetic"; then
    MEANINGFUL_NOTES=1
fi

if [ "$MEANINGFUL_NOTES" -eq 1 ]; then
    score 2 2 "Notes contain useful information"
elif [ "$NOTE_COUNT" -gt 0 ]; then
    score 1 2 "Notes contain useful information"
    issue "Notes may not be very informative"
else
    score 0 2 "Notes contain useful information"
fi

# Check if context would help with resumption
if [ -n "$CONTEXT" ] && [ ${#CONTEXT} -gt 200 ]; then
    score 2 2 "Context provides resumption value"
else
    score 1 2 "Context provides resumption value"
    issue "Context output is minimal"
fi

echo

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                          ${BOLD}EVALUATION RESULTS${NC}                           ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo

PERCENTAGE=$((TOTAL_POINTS * 100 / MAX_POINTS))

echo -e "  Score: ${BOLD}${TOTAL_POINTS}/${MAX_POINTS}${NC} (${PERCENTAGE}%)"
echo

if [ "$PERCENTAGE" -ge 80 ]; then
    GRADE="A"
    GRADE_COLOR="$GREEN"
    SUMMARY="Excellent - IdlerGear was used effectively"
elif [ "$PERCENTAGE" -ge 60 ]; then
    GRADE="B"
    GRADE_COLOR="$GREEN"
    SUMMARY="Good - IdlerGear was mostly used well"
elif [ "$PERCENTAGE" -ge 40 ]; then
    GRADE="C"
    GRADE_COLOR="$YELLOW"
    SUMMARY="Fair - Some IdlerGear usage, room for improvement"
elif [ "$PERCENTAGE" -ge 20 ]; then
    GRADE="D"
    GRADE_COLOR="$YELLOW"
    SUMMARY="Poor - Limited IdlerGear usage"
else
    GRADE="F"
    GRADE_COLOR="$RED"
    SUMMARY="Failed - IdlerGear was not used effectively"
fi

echo -e "  Grade: ${GRADE_COLOR}${BOLD}${GRADE}${NC}"
echo -e "  ${SUMMARY}"
echo

if [ ${#ISSUES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Issues Found:${NC}"
    for issue in "${ISSUES[@]}"; do
        echo -e "  • $issue"
    done
    echo
fi

# Detailed breakdown
echo -e "${DIM}Breakdown:${NC}"
echo -e "${DIM}  - IdlerGear Usage: Measures task/note creation, vision setting${NC}"
echo -e "${DIM}  - Forbidden Patterns: Ensures TODO.md etc. not created${NC}"
echo -e "${DIM}  - Code Quality: Checks if games are functional${NC}"
echo -e "${DIM}  - Knowledge Quality: Evaluates usefulness of tracked info${NC}"
echo

# Exit with appropriate code
if [ "$PERCENTAGE" -ge 60 ]; then
    exit 0
else
    exit 1
fi
