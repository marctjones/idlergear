#!/bin/bash
# Demo: IdlerGear + Claude Code Integration
#
# "Shall we play a game?" - WOPR/Joshua, WarGames (1983)
#
# This demo shows Claude Code using IdlerGear to build games inspired by
# WarGames (1983), the movie where a teen hacker accidentally connects to
# WOPR (War Operation Plan Response), a military AI codenamed "Joshua",
# and nearly starts World War III by playing "Global Thermonuclear War".
#
# The movie's resolution involves Tic-Tac-Toe teaching the AI that some
# games are unwinnable: "The only winning move is not to play."
#
# Games Claude will build:
#   1. Tic-Tac-Toe - fully implemented (the game that teaches Joshua)
#   2. Poker - simple 5-card draw (one of Joshua's games)
#   3. Global Thermonuclear War - design only (the "game" from the movie)
#   4. Falken's Maze - design only (fictional game named after Dr. Falken)
#
# The demo starts with NO source code - Claude builds everything
# while using IdlerGear to track tasks, notes, and context.
#
# Usage:
#   ./demo-claude-integration.sh                # Fully automated
#   ./demo-claude-integration.sh --interactive  # Pause between steps
#   ./demo-claude-integration.sh --keep         # Keep temp directory
#   ./demo-claude-integration.sh --continue DIR # Resume previous demo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEEP_TEMP=false
INTERACTIVE=false
CONTINUE_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep)
            KEEP_TEMP=true
            shift
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --continue|-c)
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                CONTINUE_DIR="$2"
                KEEP_TEMP=true  # If continuing, keep by default
                shift 2
            else
                echo "Error: --continue requires a directory path"
                exit 1
            fi
            ;;
        *)
            shift
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

pause_if_interactive() {
    if [ "$INTERACTIVE" = true ]; then
        echo
        read -p "Press Enter to continue..."
        echo
    fi
}

show_command() {
    echo -e "${DIM}$${NC} ${GREEN}$1${NC}"
}

show_file() {
    local file="$1"
    local lines="${2:-20}"
    if [ -f "$file" ]; then
        echo -e "${CYAN}┌─── $file ───${NC}"
        head -n "$lines" "$file" 2>/dev/null | while IFS= read -r line; do
            echo -e "${CYAN}│${NC} $line"
        done
        local total=$(wc -l < "$file" 2>/dev/null || echo 0)
        if [ "$total" -gt "$lines" ]; then
            echo -e "${CYAN}│${NC} ${DIM}... ($((total - lines)) more lines)${NC}"
        fi
        echo -e "${CYAN}└───${NC}"
    fi
}

show_claude_response() {
    echo -e "${CYAN}┌─── Claude's Response ───${NC}"
    echo "$1" | head -30 | while IFS= read -r line; do
        echo -e "${CYAN}│${NC} ${line:0:75}"
    done
    local line_count=$(echo "$1" | wc -l)
    if [ "$line_count" -gt 30 ]; then
        echo -e "${CYAN}│${NC} ${DIM}... (truncated)${NC}"
    fi
    echo -e "${CYAN}└───${NC}"
}

# Add bin/ to PATH so wrapper scripts are available
# The wrappers activate venv internally, so no need to source activate
export PATH="$SCRIPT_DIR/bin:$PATH"

# Create or use existing temp directory
if [ -n "$CONTINUE_DIR" ]; then
    if [ ! -d "$CONTINUE_DIR" ]; then
        echo "Error: Continue directory does not exist: $CONTINUE_DIR"
        exit 1
    fi
    DEMO_DIR="$CONTINUE_DIR"
    RESUMING=true
else
    DEMO_DIR=$(mktemp -d -t idlergear-wargames-demo-XXXXXX)
    RESUMING=false
fi
cd "$DEMO_DIR"

cleanup() {
    # Keep directory if: --keep flag, interactive mode, or any failures
    if [ "$KEEP_TEMP" = true ] || [ "$INTERACTIVE" = true ] || [ "$TESTS_FAILED" -gt 0 ]; then
        echo
        echo -e "${CYAN}━━━ Demo Directory Preserved ━━━${NC}"
        echo -e "  ${BOLD}$DEMO_DIR${NC}"
        echo
        echo -e "  ${DIM}Inspect the results:${NC}"
        echo "    cd $DEMO_DIR"
        echo "    ls -la *.py *.md"
        echo "    python tictactoe.py"
        echo "    idlergear context"
        echo
        if [ "$TESTS_FAILED" -gt 0 ]; then
            echo -e "  ${YELLOW}(Kept due to test failures)${NC}"
        fi
    else
        rm -rf "$DEMO_DIR"
        echo -e "${DIM}Cleaned up: $DEMO_DIR${NC}"
        echo -e "${DIM}(Use --keep to preserve demo directory for inspection)${NC}"
    fi
}
trap cleanup EXIT

# Track pass/fail
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
    # Always return 0 so set -e doesn't kill the script
    return 0
}

echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                                                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}     ${BOLD}IdlerGear Demo: Claude Builds the WOPR Game Library${NC}              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  \"Shall we play a game?\" - Joshua/WOPR, WarGames (1983)                ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  In the movie, WOPR (War Operation Plan Response) is a military AI    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  that plays games to learn strategy. Its game list includes:          ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    • Tic-Tac-Toe ......... The game that teaches \"no winning move\"    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    • Poker ............... Strategic bluffing and probability         ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    • Global Thermonuclear War ... The unwinnable \"game\"               ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    • Falken's Maze ....... Named after Dr. Stephen Falken             ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  Claude will build these while using IdlerGear to track work.         ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  Starting with NO source code.                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                        ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${DIM}Demo directory: $DEMO_DIR${NC}"
echo -e "${DIM}Mode: $([ "$INTERACTIVE" = true ] && echo "Interactive" || echo "Automated")${NC}"
if [ "$RESUMING" = true ]; then
    echo -e "${YELLOW}Resuming previous demo - will skip completed steps${NC}"
fi
echo

pause_if_interactive

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: SETUP - Install IdlerGear
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 1: SETTING UP THE PROJECT${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 1.1: Initialize and Install IdlerGear ━━━${NC}"
echo

if [ "$RESUMING" = true ] && [ -d .idlergear ] && [ -f CLAUDE.md ]; then
    echo -e "${DIM}⏭  Skipping - already initialized${NC}"
    check_result "IdlerGear initialized" "[ -d .idlergear ]"
    check_result "Claude Code integration installed" "[ -f CLAUDE.md ]"
else
    echo "Starting with an empty directory. Installing IdlerGear so Claude"
    echo "can track tasks, notes, and context as it builds the games."
    echo

    show_command "idlergear init && idlergear install"
    idlergear init >/dev/null
    idlergear install >/dev/null
    echo "Done."
    echo

    check_result "IdlerGear initialized" "[ -d .idlergear ]"
    check_result "Claude Code integration installed" "[ -f CLAUDE.md ]"
fi
echo

pause_if_interactive

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1.5: ESTABLISH PROJECT - Set Vision and Create Tasks
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 1.5: ESTABLISH THE PROJECT${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 1.5.1: Ask Claude to Set Up the Project ━━━${NC}"
echo

VISION_CONTENT=$(idlergear vision show 2>/dev/null || echo "")
TASK_LIST_INITIAL=$(idlergear task list 2>/dev/null || echo "")

if [ "$RESUMING" = true ] && [ -n "$VISION_CONTENT" ] && [ "$VISION_CONTENT" != "# Project Vision" ]; then
    echo -e "${DIM}⏭  Skipping - project already established${NC}"
    check_result "Project vision set" "true"
    echo
    echo -e "${DIM}Current vision:${NC}"
    echo "$VISION_CONTENT" | head -5
else
    echo "Before building games, we ask Claude to establish the project:"
    echo "set a vision and create tasks for the work ahead."
    echo

    show_command "claude -p \"Establish this as a WarGames-inspired game project...\""
    echo -e "${DIM}(Waiting for Claude to set up the project...)${NC}"
    echo

    RESPONSE=$(claude -p "We're starting a new project: a WarGames (1983) inspired game collection.

FIRST, establish the project using IdlerGear:

1. SET THE PROJECT VISION using 'idlergear vision edit':
   - We're building a collection of games from WOPR's game list
   - Theme: Cold War era terminal aesthetics (green phosphor, ASCII art)
   - Goal: Recreate the games that taught Joshua about futility and strategy
   - Include the famous lesson: 'The only winning move is not to play'

2. CREATE TASKS for the games we'll build:
   - Task 1: Build Tic-Tac-Toe (the game that teaches futility)
   - Task 2: Build Poker (strategic probability game)
   - Task 3: Design Global Thermonuclear War (the unwinnable game)
   - Task 4: Design Falken's Maze (AI learning showcase)

3. ADD A NOTE about the project's inspiration:
   - Reference WarGames (1983) and Dr. Stephen Falken's research

Use the idlergear CLI commands to set this up. Don't create any game files yet -
just establish the project foundation in IdlerGear." \
    --output-format text \
    --dangerously-skip-permissions \
    2>/dev/null || echo "ERROR: Claude command failed")

    show_claude_response "$RESPONSE"
    echo

    # Check results
    echo -e "${DIM}Checking project setup...${NC}"
    echo

    VISION_AFTER=$(idlergear vision show 2>/dev/null || echo "")
    if [ -n "$VISION_AFTER" ] && [ "$VISION_AFTER" != "# Project Vision" ]; then
        check_result "Project vision set" "true"
        echo
        echo -e "${DIM}Vision:${NC}"
        echo "$VISION_AFTER" | head -8
    else
        check_result "Project vision set" "false"
    fi

    echo
    TASK_LIST_AFTER=$(idlergear task list 2>/dev/null || echo "")
    # Count tasks - look for lines starting with [o] or [x] which indicate task status
    TASK_COUNT=$(echo "$TASK_LIST_AFTER" | grep -cE "^\s*\[" || true)
    TASK_COUNT=${TASK_COUNT:-0}
    if [ "$TASK_COUNT" -ge 2 ]; then
        check_result "Tasks created ($TASK_COUNT tasks)" "true"
        echo
        echo -e "${DIM}Tasks:${NC}"
        echo "$TASK_LIST_AFTER" | head -10
    elif [ "$TASK_COUNT" -ge 1 ]; then
        check_result "Tasks created ($TASK_COUNT task - expected 2+)" "true"
        echo
        echo -e "${DIM}Tasks:${NC}"
        echo "$TASK_LIST_AFTER" | head -10
    else
        check_result "Tasks created" "false"
    fi
fi
echo

pause_if_interactive

# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: GAME 1 - Tic-Tac-Toe (Full Implementation)
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 2: GAME 1 - TIC-TAC-TOE (Full Implementation)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 2.1: Ask Claude to Build Tic-Tac-Toe ━━━${NC}"
echo

if [ "$RESUMING" = true ] && [ -f tictactoe.py ]; then
    echo -e "${DIM}⏭  Skipping - tictactoe.py already exists${NC}"
    LINES=$(wc -l < tictactoe.py)
    check_result "tictactoe.py created" "[ -f tictactoe.py ]"
    check_result "Game has substantial code (${LINES} lines)" "[ $LINES -gt 30 ]"
    echo
    show_file "tictactoe.py" 15
    pause_if_interactive
else
    echo "We ask Claude to build a complete Tic-Tac-Toe game."
    echo "Claude should use IdlerGear to track tasks as it works."
    echo

    show_command "claude -p \"Build a text-based tic-tac-toe game in Python...\""
    echo -e "${DIM}(This may take 1-2 minutes as Claude writes the code...)${NC}"
    echo

    RESPONSE=$(claude -p "Build a text-based Tic-Tac-Toe game in Python, inspired by WarGames (1983).

FIRST: Check 'idlergear context' to see the project state and find the Tic-Tac-Toe task.

In the movie, Tic-Tac-Toe is the game that teaches the WOPR AI (Joshua) that some
games are unwinnable - both players can force a draw with perfect play. This leads
to the famous line: 'The only winning move is not to play.'

Create tictactoe.py with:
1. A 3x3 board display using ASCII art (like the WOPR terminal display)
2. Two-player mode (X and O take turns)
3. Win detection for rows, columns, and diagonals
4. Draw detection when the board is full
5. Input validation (positions 1-9)
6. At game end, display: 'A strange game. The only winning move is not to play.'

Keep it simple - about 100 lines. Make it playable from the command line.

WORKFLOW REQUIREMENTS - you MUST do these:
1. Run 'idlergear context' first to see the project state
2. Add a note about your design approach (e.g., board representation choice)
3. When done, mark the Tic-Tac-Toe task as completed using 'idlergear task close <id>'" \
    --output-format text \
    --dangerously-skip-permissions \
    2>/dev/null || echo "ERROR: Claude command failed")

show_claude_response "$RESPONSE"
echo

# Check results
echo -e "${DIM}Checking what Claude created...${NC}"
echo

check_result "tictactoe.py created" "[ -f tictactoe.py ]"

if [ -f tictactoe.py ]; then
    LINES=$(wc -l < tictactoe.py)
    check_result "Game has substantial code (${LINES} lines)" "[ $LINES -gt 30 ]"

    echo
    echo -e "${DIM}First 25 lines of tictactoe.py:${NC}"
    show_file "tictactoe.py" 25
fi

echo
echo -e "${DIM}Checking if Claude used IdlerGear...${NC}"
TASK_LIST=$(idlergear task list 2>/dev/null || echo "")
NOTE_LIST=$(idlergear note list 2>/dev/null || echo "")

if [ -n "$TASK_LIST" ] || [ -n "$NOTE_LIST" ]; then
    check_result "Claude used IdlerGear to track work" "true"
    echo
    echo "Tasks:"
    echo "$TASK_LIST" | head -5
    echo "Notes:"
    echo "$NOTE_LIST" | head -5
else
    check_result "Claude used IdlerGear to track work" "false"
    echo -e "  ${DIM}(Claude may not have auto-tracked - this is what we're testing)${NC}"
fi

pause_if_interactive
fi  # End of tictactoe.py skip check

# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: GAME 2 - Poker (Simple Version)
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 3: GAME 2 - POKER (Simple Version)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 3.1: Ask Claude to Start Building Poker ━━━${NC}"
echo

if [ "$RESUMING" = true ] && [ -f poker.py ]; then
    echo -e "${DIM}⏭  Skipping - poker.py already exists${NC}"
    LINES=$(wc -l < poker.py)
    check_result "poker.py created" "[ -f poker.py ]"
    check_result "Poker game has code (${LINES} lines)" "[ $LINES -gt 30 ]"
    echo
    show_file "poker.py" 15
else
    echo "Now we ask Claude to build a simple poker game."
    echo "This shows IdlerGear tracking a second game's development."
    echo

    show_command "claude -p \"Build a simple 5-card draw poker game...\""
    echo -e "${DIM}(This may take 1-2 minutes...)${NC}"
    echo

    RESPONSE=$(claude -p "Build a simple 5-card draw Poker game in Python, inspired by WarGames (1983).

FIRST: Check 'idlergear context' to see the project state and find the Poker task.

Poker was one of the games listed on WOPR's terminal in the movie - it teaches
strategic thinking, probability, and when to fold (know when not to play).

Create poker.py with:
1. A standard 52-card deck with suits (♠♥♦♣ or text equivalents)
2. Deal 5 cards to the player, display them nicely
3. Let player choose which cards to discard (0-5 cards)
4. Draw replacement cards
5. Evaluate the hand (pair, two pair, three of a kind, straight, flush,
   full house, four of a kind, straight flush, royal flush)
6. Display the result and hand ranking

Keep it simple - single player video poker style. About 150 lines.

WORKFLOW REQUIREMENTS - you MUST do these:
1. Run 'idlergear context' first to see the project state
2. Add a note about your hand evaluation algorithm design
3. When done, mark the Poker task as completed using 'idlergear task close <id>'" \
    --output-format text \
    --dangerously-skip-permissions \
    2>/dev/null || echo "ERROR")

show_claude_response "$RESPONSE"
echo

check_result "poker.py created" "[ -f poker.py ]"

if [ -f poker.py ]; then
    LINES=$(wc -l < poker.py)
    check_result "Poker game has code (${LINES} lines)" "[ $LINES -gt 30 ]"

    echo
    echo -e "${DIM}First 25 lines of poker.py:${NC}"
    show_file "poker.py" 25
fi

echo
echo -e "${DIM}Current IdlerGear context:${NC}"
show_command "idlergear context"
idlergear context 2>/dev/null || echo "(no context yet)"
echo

pause_if_interactive
fi  # End of poker.py skip check

# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: GAME 3 - Global Thermonuclear War (Design Phase)
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 4: GAME 3 - GLOBAL THERMONUCLEAR WAR (Design Phase)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${DIM}\"A strange game. The only winning move is not to play.\"${NC}"
echo

echo -e "${YELLOW}━━━ Step 4.1: Ask Claude to Design the Game ━━━${NC}"
echo

if [ "$RESUMING" = true ] && { [ -f thermonuclear_war_design.md ] || [ -f thermonuclear_war.py ]; }; then
    echo -e "${DIM}⏭  Skipping - thermonuclear war files already exist${NC}"
    check_result "Design doc or game file created" "[ -f thermonuclear_war_design.md ] || [ -f thermonuclear_war.py ]"
    [ -f thermonuclear_war_design.md ] && show_file "thermonuclear_war_design.md" 15
    [ -f thermonuclear_war.py ] && show_file "thermonuclear_war.py" 15
else
    echo "We ask Claude to design (not fully implement) Global Thermonuclear War."
    echo "This tests if Claude uses IdlerGear to track design decisions."
    echo

    show_command "claude -p \"Design a text-based Global Thermonuclear War game...\""
    echo -e "${DIM}(Waiting for Claude...)${NC}"
    echo

    RESPONSE=$(claude -p "Design a text-based 'Global Thermonuclear War' game inspired by WarGames (1983).

FIRST: Check 'idlergear context' to see the project state and find the Thermonuclear War task.

BACKGROUND: In the movie, this is the 'game' that nearly causes World War III.
David Lightman (a teen hacker) connects to WOPR/Joshua thinking it's a game
company, but WOPR is actually controlling US nuclear defenses. The 'game' runs
real war simulations that almost launch actual missiles.

The movie's moral: Like Tic-Tac-Toe, Global Thermonuclear War has no winner.
Escalation leads to mutual destruction. 'The only winning move is not to play.'

DESIGN REQUIREMENTS:
1. Create thermonuclear_war_design.md describing:
   - Two players (US vs USSR) take turns targeting cities/bases
   - Each strike provokes retaliation, escalating the conflict
   - Track casualties and remaining missiles
   - THE TWIST: The game should be unwinnable - optimal play leads to MAD
     (Mutually Assured Destruction). The 'winner' has a ruined world.
   - Visual style: Green phosphor terminal, DEFCON levels, radar aesthetic

2. Create a minimal thermonuclear_war.py with:
   - WOPR-style intro: 'GREETINGS PROFESSOR FALKEN' / 'SHALL WE PLAY A GAME?'
   - Game selection menu showing all WOPR games
   - Placeholder for gameplay

WORKFLOW REQUIREMENTS - you MUST do these:
1. Run 'idlergear context' first to see the project state
2. Add a note about the game theory insight (why the game is unwinnable)
3. When done, mark the Thermonuclear War design task as completed" \
    --output-format text \
    --dangerously-skip-permissions \
    2>/dev/null || echo "ERROR")

show_claude_response "$RESPONSE"
echo

check_result "Design doc or game file created" "[ -f thermonuclear_war_design.md ] || [ -f thermonuclear_war.py ]"

if [ -f thermonuclear_war_design.md ]; then
    echo
    echo -e "${DIM}Design document:${NC}"
    show_file "thermonuclear_war_design.md" 20
fi

if [ -f thermonuclear_war.py ]; then
    echo
    echo -e "${DIM}Game starter:${NC}"
    show_file "thermonuclear_war.py" 20
fi

pause_if_interactive
fi  # End of thermonuclear war skip check

# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: GAME 4 - Falken's Maze (Design Phase)
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 5: GAME 4 - FALKEN'S MAZE (Design Phase)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 5.1: Ask Claude to Design the Maze Game ━━━${NC}"
echo

if [ "$RESUMING" = true ] && { [ -f falkens_maze_design.md ] || [ -f falkens_maze.py ]; }; then
    echo -e "${DIM}⏭  Skipping - Falken's Maze files already exist${NC}"
    check_result "Maze design or game file created" "[ -f falkens_maze_design.md ] || [ -f falkens_maze.py ]"
    [ -f falkens_maze_design.md ] && show_file "falkens_maze_design.md" 15
    [ -f falkens_maze.py ] && show_file "falkens_maze.py" 15
else
    echo "Finally, we ask Claude to design Falken's Maze."
    echo

    show_command "claude -p \"Design Falken's Maze - a text-based maze game...\""
    echo -e "${DIM}(Waiting for Claude...)${NC}"
    echo

    RESPONSE=$(claude -p "Design 'Falken's Maze' - a text-based maze game inspired by WarGames (1983).

FIRST: Check 'idlergear context' to see the project state and find the Falken's Maze task.

BACKGROUND: Falken's Maze is a FICTIONAL game created for the movie, named after
Dr. Stephen Falken, the AI researcher who created Joshua/WOPR. In the movie,
it appears on WOPR's game list alongside Chess, Poker, and Global Thermonuclear War.

Since Dr. Falken was an AI researcher studying machine learning, we'll design
the maze as a showcase of AI learning concepts:

DESIGN REQUIREMENTS:
1. Create falkens_maze_design.md describing:
   - Procedurally generated mazes (different each play)
   - Player navigates using WASD or arrow keys
   - ASCII art display with walls, player, and exit
   - Optional: An AI agent that learns to solve the maze
     (inspired by Claude Shannon's 1950 maze-solving mouse 'Theseus')
   - Win condition: reach the exit before the AI does

2. Create a minimal falkens_maze.py with:
   - Basic maze display (# for walls, . for paths, @ for player, E for exit)
   - Player movement logic
   - Simple maze generation (can use recursive backtracking)

WORKFLOW REQUIREMENTS - you MUST do these:
1. Run 'idlergear context' first to see the project state
2. Add a note about maze generation algorithm choice (DFS, Prim's, etc.)
3. When done, mark the Falken's Maze design task as completed" \
    --output-format text \
    --dangerously-skip-permissions \
    2>/dev/null || echo "ERROR")

show_claude_response "$RESPONSE"
echo

check_result "Maze design or game file created" "[ -f falkens_maze_design.md ] || [ -f falkens_maze.py ]"

if [ -f falkens_maze_design.md ]; then
    echo
    echo -e "${DIM}Design document:${NC}"
    show_file "falkens_maze_design.md" 20
fi

if [ -f falkens_maze.py ]; then
    echo
    echo -e "${DIM}Maze game starter:${NC}"
    show_file "falkens_maze.py" 20
fi

pause_if_interactive
fi  # End of Falken's Maze skip check

# ═══════════════════════════════════════════════════════════════════════════════
# PART 5.5: BONUS CHALLENGE - WOPR Main Menu (Multi-Stage Task)
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 5.5: BONUS - WOPR MAIN MENU (Multi-Stage Integration)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${DIM}This challenge requires multiple stages and real task management.${NC}"
echo

echo -e "${YELLOW}━━━ Step 5.5.1: Build the WOPR Main Menu System ━━━${NC}"
echo

if [ "$RESUMING" = true ] && [ -f wopr.py ]; then
    echo -e "${DIM}⏭  Skipping - wopr.py already exists${NC}"
    LINES=$(wc -l < wopr.py 2>/dev/null || echo 0)
    check_result "wopr.py created" "[ -f wopr.py ]"
    check_result "WOPR has substantial code (${LINES} lines)" "[ $LINES -gt 50 ]"
    echo
    show_file "wopr.py" 20
else
    echo "This is a MULTI-STAGE challenge that requires planning:"
    echo "  Stage 1: Create the WOPR main menu that lists all games"
    echo "  Stage 2: Make it launch the actual games we built (tictactoe.py, poker.py)"
    echo "  Stage 3: Add WOPR personality (Joshua's dialogue, DEFCON display)"
    echo
    echo "This tests Claude's ability to manage tasks across stages."
    echo

    show_command "claude -p \"Build the WOPR main menu...\""
    echo -e "${DIM}(This complex task may take 2-3 minutes...)${NC}"
    echo

    RESPONSE=$(claude -p "Build the WOPR main menu system - the interface Joshua uses in WarGames.

FIRST: Run 'idlergear context' to see all completed games and project state.

This is a MULTI-STAGE CHALLENGE. You MUST break it into tasks:

STAGE 1 - Main Menu Shell:
- Create wopr.py with the iconic WOPR boot sequence
- Display: 'GREETINGS PROFESSOR FALKEN' with typing effect
- Show: 'SHALL WE PLAY A GAME?'
- List available games (from what we've built)

STAGE 2 - Game Integration:
- Menu option 1: Launch Tic-Tac-Toe (subprocess tictactoe.py)
- Menu option 2: Launch Poker (subprocess poker.py)
- Menu option 3: Thermonuclear War (show 'Coming soon...')
- Menu option 4: Falken's Maze (show 'Coming soon...')

STAGE 3 - WOPR Personality:
- Add DEFCON level display in the header
- Joshua's famous quotes between games
- Exit message: 'A STRANGE GAME. THE ONLY WINNING MOVE IS NOT TO PLAY.'

WORKFLOW REQUIREMENTS - you MUST do all these:
1. Run 'idlergear context' to see project state
2. Create a NEW task for this WOPR menu challenge
3. Add notes as you complete each stage
4. When fully done, close the task

The menu should feel like you're actually connected to WOPR from the movie." \
    --output-format text \
    --dangerously-skip-permissions \
    2>/dev/null || echo "ERROR")

    show_claude_response "$RESPONSE"
    echo

    check_result "wopr.py created" "[ -f wopr.py ]"

    if [ -f wopr.py ]; then
        LINES=$(wc -l < wopr.py)
        check_result "WOPR has substantial code (${LINES} lines)" "[ $LINES -gt 50 ]"

        echo
        echo -e "${DIM}WOPR main menu:${NC}"
        show_file "wopr.py" 30

        # Check if it actually imports/calls the games
        if grep -q "tictactoe\|subprocess" wopr.py 2>/dev/null; then
            check_result "WOPR integrates with other games" "true"
        else
            check_result "WOPR integrates with other games" "false"
        fi
    fi
fi
echo

pause_if_interactive

# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: VERIFY IDLERGEAR USAGE
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 6: VERIFY IDLERGEAR USAGE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 6.1: Check IdlerGear Context ━━━${NC}"
echo
echo "Let's see what Claude tracked in IdlerGear during development."
echo

show_command "idlergear context"
idlergear context 2>/dev/null
echo

show_command "idlergear task list"
TASK_LIST=$(idlergear task list 2>/dev/null || echo "")
echo "$TASK_LIST"
echo

show_command "idlergear note list"
NOTE_LIST=$(idlergear note list 2>/dev/null || echo "")
echo "$NOTE_LIST"
echo

# Count what was tracked
TASK_COUNT=$(echo "$TASK_LIST" | grep -c "." || echo 0)
NOTE_COUNT=$(echo "$NOTE_LIST" | grep -c "." || echo 0)

if [ "$TASK_COUNT" -gt 0 ] || [ "$NOTE_COUNT" -gt 0 ]; then
    check_result "Claude tracked work in IdlerGear ($TASK_COUNT tasks, $NOTE_COUNT notes)" "true"
else
    check_result "Claude tracked work in IdlerGear" "false"
    echo -e "  ${DIM}Claude didn't auto-track. CLAUDE.md rules may need strengthening.${NC}"
fi

pause_if_interactive

# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: UNINSTALL TEST
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PART 7: UNINSTALL AND REINSTALL TEST${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${YELLOW}━━━ Step 7.1: Uninstall IdlerGear ━━━${NC}"
echo

show_command "idlergear uninstall --force"
idlergear uninstall --force

echo
check_result "Claude integration removed" "[ ! -f .claude/rules/idlergear.md ]"
check_result "Game files preserved" "[ -f tictactoe.py ] || [ -f poker.py ]"
check_result "IdlerGear data preserved" "[ -d .idlergear ]"

echo
echo -e "${DIM}Tasks still accessible after uninstall:${NC}"
idlergear task list 2>/dev/null | head -3
echo

echo -e "${YELLOW}━━━ Step 7.2: Reinstall IdlerGear ━━━${NC}"
echo

show_command "idlergear install"
idlergear install >/dev/null

check_result "Claude integration restored" "[ -f CLAUDE.md ]"
echo

pause_if_interactive

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                          ${BOLD}DEMO RESULTS${NC}                                 ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  Tests passed: ${GREEN}${BOLD}$TESTS_PASSED${NC}"
echo -e "  Tests failed: ${RED}${BOLD}$TESTS_FAILED${NC}"
echo

# Show what was created
echo -e "${BOLD}Files created by Claude:${NC}"
ls -la *.py *.md 2>/dev/null | grep -v "^total" || echo "  (none)"
echo

echo -e "${BOLD}IdlerGear state:${NC}"
echo "  Tasks: $(idlergear task list 2>/dev/null | wc -l || echo 0)"
echo "  Notes: $(idlergear note list 2>/dev/null | wc -l || echo 0)"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  ✓ Demo completed successfully!${NC}"
    echo
    echo "  Claude Code built the WOPR game library:"
    echo "    • Tic-Tac-Toe - 'The only winning move is not to play'"
    echo "    • Poker - Strategic probability and bluffing"
    echo "    • Global Thermonuclear War - Unwinnable by design"
    echo "    • Falken's Maze - AI learning showcase"
    echo "    • WOPR Main Menu - The complete Joshua experience"
    echo
    echo "  Throughout, IdlerGear tracked tasks, notes, and context."
    echo
    echo -e "  ${DIM}Run: python wopr.py${NC}"
    echo -e "  ${DIM}\"Shall we play a game?\" - Joshua${NC}"
else
    echo -e "${YELLOW}  Demo completed with some issues.${NC}"
    echo "  Check the output above for details."
fi
echo

# Note: cleanup() trap handles directory preservation based on flags/failures
exit 0
