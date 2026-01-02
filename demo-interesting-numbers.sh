#!/bin/bash
# =============================================================================
# IdlerGear Demo: Setting up a new project from scratch
# =============================================================================
#
# This demo shows how to:
# 1. Create a new Python project with IdlerGear
# 2. Set project vision and create tasks
# 3. Add notes and reference documentation
# 4. Configure GitHub backend (optional)
#
# Prerequisites:
# - IdlerGear installed (pip install idlergear or from source)
# - gh CLI installed and authenticated (for GitHub backend)
#
# Usage:
#   ./demo-interesting-numbers.sh
#
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project settings
PROJECT_NAME="interesting-numbers"
PROJECT_DIR="/tmp/${PROJECT_NAME}"

# Helper functions
header() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

step() {
    echo -e "${GREEN}▶ $1${NC}"
}

info() {
    echo -e "${BLUE}  ℹ $1${NC}"
}

run() {
    echo -e "${YELLOW}  \$ $1${NC}"
    eval "$1"
    echo ""
}

# =============================================================================
# DEMO START
# =============================================================================

header "IdlerGear Demo: Creating 'Interesting Numbers' Project from Scratch"

echo "This demo will create a complete Python project using IdlerGear commands."
echo "The project will calculate various interesting numbers (primes, Fibonacci, etc.)"
echo ""
echo "Project will be created at: ${PROJECT_DIR}"
echo ""

# Clean up any previous run
if [ -d "${PROJECT_DIR}" ]; then
    step "Cleaning up previous demo..."
    rm -rf "${PROJECT_DIR}"
    echo ""
fi

# -----------------------------------------------------------------------------
# Step 1: Create New Project with IdlerGear
# -----------------------------------------------------------------------------
header "Step 1: Create New Project"

step "Creating new Python project with IdlerGear..."
run "idlergear new ${PROJECT_NAME} --path /tmp --python --vision 'A Python library for generating and analyzing mathematically interesting numbers' --description 'Educational tool for number theory' --no-venv"

step "Moving into project directory..."
cd "${PROJECT_DIR}"
run "pwd"

step "Checking the created structure..."
run "ls -la"

step "Checking .idlergear/ structure..."
run "ls -la .idlergear/"

# -----------------------------------------------------------------------------
# Step 2: Update Project Vision
# -----------------------------------------------------------------------------
header "Step 2: Set Detailed Project Vision"

step "Updating project vision with full details..."

# Use idlergear vision edit would open an editor, so we'll write directly
# In a real workflow you'd use: idlergear vision edit
# Note: v0.3 schema uses .idlergear/vision/VISION.md
cat > .idlergear/vision/VISION.md << 'VISION_EOF'
# Interesting Numbers Library

## Purpose

A Python library for generating and analyzing mathematically interesting numbers,
designed as both an educational tool and a practical utility.

## Principles

1. **Correctness First** - Mathematical accuracy is non-negotiable
2. **Performance Aware** - Efficient algorithms for large number ranges
3. **Well Documented** - Every function should be self-explanatory
4. **Thoroughly Tested** - Comprehensive test coverage

## Goals

- [ ] Implement core number types (primes, Fibonacci, perfect, triangular)
- [ ] Add CLI interface for quick calculations
- [ ] Create comprehensive documentation with examples
- [ ] Optimize algorithms for numbers up to 10^9

## Number Types to Support

- **Primes**: Numbers divisible only by 1 and themselves
- **Fibonacci**: Each number is the sum of two preceding ones
- **Perfect Numbers**: Equal to the sum of their proper divisors
- **Triangular Numbers**: 1, 3, 6, 10, 15... (n*(n+1)/2)
- **Palindromes**: Numbers that read the same forwards and backwards
- **Factorials**: n! = n * (n-1) * ... * 1
VISION_EOF

run "idlergear vision show"

# -----------------------------------------------------------------------------
# Step 3: Create Tasks for Development
# -----------------------------------------------------------------------------
header "Step 3: Create Development Tasks"

step "Creating tasks for implementing number types..."

run "idlergear task create 'Implement prime number functions' --body 'Create is_prime() and primes() generator using trial division' --label enhancement --label core"

run "idlergear task create 'Implement Fibonacci sequence' --body 'Create fibonacci(n) and fibonacci_sequence() generator' --label enhancement --label core"

run "idlergear task create 'Add perfect number detection' --body 'Create is_perfect() and perfect_numbers() generator. Note: only 4 perfect numbers below 10000' --label enhancement"

run "idlergear task create 'Add triangular numbers' --body 'Create triangular(n) and triangular_numbers() generator using formula n*(n+1)/2' --label enhancement"

run "idlergear task create 'Add palindrome detection' --body 'Create is_palindrome() for checking if a number reads same forwards and backwards' --label enhancement"

run "idlergear task create 'Implement factorial function' --body 'Create factorial(n) with proper error handling for negative numbers' --label enhancement"

step "Creating infrastructure tasks..."

run "idlergear task create 'Write comprehensive unit tests' --body 'Test all number functions with edge cases' --label testing --priority high"

run "idlergear task create 'Add CLI interface' --body 'Create command-line interface using argparse or typer' --label feature"

run "idlergear task create 'Optimize prime sieve for large ranges' --body 'Implement Sieve of Eratosthenes for O(n log log n) performance' --label performance"

run "idlergear task create 'Add type hints and docstrings' --body 'Full type annotations and Google-style docstrings' --label documentation"

step "Listing all tasks..."
run "idlergear task list"

# -----------------------------------------------------------------------------
# Step 4: Create Development Notes
# -----------------------------------------------------------------------------
header "Step 4: Add Development Notes"

step "Adding algorithm notes..."

run "idlergear note create 'Consider using Sieve of Eratosthenes for prime generation - O(n log log n) vs O(n sqrt n) for trial division. For ranges up to 10^6, sieve is ~100x faster.' --tag idea --tag performance"

run "idlergear note create 'Perfect numbers are rare: only 6, 28, 496, 8128 below 10000. All known perfect numbers are even. Related to Mersenne primes via formula 2^(p-1) * (2^p - 1).' --tag research"

run "idlergear note create 'Binet formula for Fibonacci has floating point precision issues for n > 70. Use matrix exponentiation or iterative method instead.' --tag idea --tag algorithm"

run "idlergear note create 'Consider adding Lucas numbers - similar to Fibonacci but starts with 2, 1. Many interesting relationships with Fibonacci sequence.' --tag idea --tag feature"

step "Listing notes..."
run "idlergear note list"

# -----------------------------------------------------------------------------
# Step 5: Add Reference Documentation
# -----------------------------------------------------------------------------
header "Step 5: Add Reference Documentation"

step "Adding algorithm reference docs..."

run "idlergear reference add 'Prime Number Algorithms' --body '## Trial Division
Time: O(sqrt n) per number
Simple but slow for ranges.

## Sieve of Eratosthenes
Time: O(n log log n) for range [2, n]
Space: O(n)
Best for generating all primes up to n.

## Miller-Rabin
Probabilistic primality test.
Time: O(k log^3 n) where k is rounds.
Best for testing single large numbers.'"

run "idlergear reference add 'Number Theory Formulas' --body '## Triangular Numbers
T(n) = n(n+1)/2
Sequence: 1, 3, 6, 10, 15, 21...

## Fibonacci
F(n) = F(n-1) + F(n-2)
F(0) = 0, F(1) = 1

## Perfect Numbers
Sum of proper divisors equals the number.
Known: 6, 28, 496, 8128, 33550336...

## Factorial
n! = n * (n-1) * ... * 2 * 1
0! = 1 by convention'"

run "idlergear reference add 'Python Best Practices' --body '## Type Hints
Use typing module for complex types.
Example: def primes(limit: int) -> Iterator[int]

## Generators
Use yield for memory-efficient sequences.
Allows processing infinite sequences.

## Testing
Use pytest with parametrized tests.
Test edge cases: 0, 1, negative, large numbers.'"

step "Listing reference docs..."
run "idlergear reference list"

# -----------------------------------------------------------------------------
# Step 6: Create the Python Source Files
# -----------------------------------------------------------------------------
header "Step 6: Create Python Source Code"

step "Creating main library file..."

mkdir -p src/interesting_numbers

cat > src/interesting_numbers/numbers.py << 'PYEOF'
"""Interesting Numbers Library.

A collection of functions for generating and checking various
types of mathematically interesting numbers.
"""

from typing import Iterator


def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def primes(limit: int) -> Iterator[int]:
    """Generate prime numbers up to limit."""
    for n in range(2, limit + 1):
        if is_prime(n):
            yield n


def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number (0-indexed)."""
    if n < 0:
        raise ValueError("Fibonacci not defined for negative indices")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_sequence(limit: int) -> Iterator[int]:
    """Generate Fibonacci numbers up to limit."""
    a, b = 0, 1
    while a <= limit:
        yield a
        a, b = b, a + b


def is_perfect(n: int) -> bool:
    """Check if n is a perfect number (equals sum of proper divisors)."""
    if n < 2:
        return False
    divisor_sum = 1
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            divisor_sum += i
            if i != n // i:
                divisor_sum += n // i
    return divisor_sum == n


def perfect_numbers(limit: int) -> Iterator[int]:
    """Generate perfect numbers up to limit."""
    for n in range(2, limit + 1):
        if is_perfect(n):
            yield n


def is_palindrome(n: int) -> bool:
    """Check if a number is a palindrome."""
    s = str(abs(n))
    return s == s[::-1]


def triangular(n: int) -> int:
    """Return the nth triangular number."""
    if n < 1:
        raise ValueError("Triangular numbers start at n=1")
    return n * (n + 1) // 2


def triangular_numbers(limit: int) -> Iterator[int]:
    """Generate triangular numbers up to limit."""
    n = 1
    while True:
        t = triangular(n)
        if t > limit:
            break
        yield t
        n += 1


if __name__ == "__main__":
    print("=== Interesting Numbers Demo ===\n")

    print("First 10 primes:", list(primes(30)))
    print("First 10 Fibonacci:", [fibonacci(i) for i in range(10)])
    print("Factorials 1-7:", [factorial(i) for i in range(1, 8)])
    print("Perfect numbers < 10000:", list(perfect_numbers(10000)))
    print("Triangular numbers < 100:", list(triangular_numbers(100)))
    print("Palindrome check 12321:", is_palindrome(12321))
PYEOF

info "Created src/interesting_numbers/numbers.py"

step "Creating test file..."

mkdir -p tests

cat > tests/test_numbers.py << 'TESTEOF'
"""Tests for the interesting numbers library."""

import pytest
from interesting_numbers.numbers import (
    is_prime,
    primes,
    factorial,
    fibonacci,
    fibonacci_sequence,
    is_perfect,
    perfect_numbers,
    is_palindrome,
    triangular,
    triangular_numbers,
)


class TestPrimes:
    def test_is_prime_small(self):
        assert not is_prime(0)
        assert not is_prime(1)
        assert is_prime(2)
        assert is_prime(3)
        assert not is_prime(4)
        assert is_prime(5)

    def test_is_prime_larger(self):
        assert is_prime(97)
        assert not is_prime(100)
        assert is_prime(101)

    def test_primes_generator(self):
        assert list(primes(20)) == [2, 3, 5, 7, 11, 13, 17, 19]


class TestFactorial:
    def test_factorial_base_cases(self):
        assert factorial(0) == 1
        assert factorial(1) == 1

    def test_factorial_values(self):
        assert factorial(5) == 120
        assert factorial(7) == 5040

    def test_factorial_negative(self):
        with pytest.raises(ValueError):
            factorial(-1)


class TestFibonacci:
    def test_fibonacci_base_cases(self):
        assert fibonacci(0) == 0
        assert fibonacci(1) == 1

    def test_fibonacci_values(self):
        assert fibonacci(10) == 55
        assert fibonacci(15) == 610

    def test_fibonacci_sequence(self):
        assert list(fibonacci_sequence(20)) == [0, 1, 1, 2, 3, 5, 8, 13]


class TestPerfectNumbers:
    def test_is_perfect(self):
        assert is_perfect(6)  # 1 + 2 + 3 = 6
        assert is_perfect(28)  # 1 + 2 + 4 + 7 + 14 = 28
        assert not is_perfect(12)

    def test_perfect_numbers_generator(self):
        assert list(perfect_numbers(30)) == [6, 28]


class TestPalindromes:
    def test_is_palindrome(self):
        assert is_palindrome(12321)
        assert is_palindrome(1001)
        assert not is_palindrome(12345)
        assert is_palindrome(7)


class TestTriangular:
    def test_triangular(self):
        assert triangular(1) == 1
        assert triangular(4) == 10
        assert triangular(7) == 28

    def test_triangular_numbers_generator(self):
        assert list(triangular_numbers(15)) == [1, 3, 6, 10, 15]
TESTEOF

info "Created tests/test_numbers.py"

step "Creating __init__.py..."
cat > src/interesting_numbers/__init__.py << 'INITEOF'
"""Interesting Numbers - A library for mathematical number sequences."""

from interesting_numbers.numbers import (
    is_prime,
    primes,
    factorial,
    fibonacci,
    fibonacci_sequence,
    is_perfect,
    perfect_numbers,
    is_palindrome,
    triangular,
    triangular_numbers,
)

__version__ = "0.1.0"
__all__ = [
    "is_prime",
    "primes",
    "factorial",
    "fibonacci",
    "fibonacci_sequence",
    "is_perfect",
    "perfect_numbers",
    "is_palindrome",
    "triangular",
    "triangular_numbers",
]
INITEOF

info "Created src/interesting_numbers/__init__.py"

step "Checking created source files..."
run "ls -la src/interesting_numbers/"
run "ls -la tests/"

# -----------------------------------------------------------------------------
# Step 7: Mark Some Tasks as Completed
# -----------------------------------------------------------------------------
header "Step 7: Update Task Status"

step "Marking core tasks as completed (we just implemented them!)..."

# Close the implementation tasks since we created the code
run "idlergear task close 1"
run "idlergear task close 2"
run "idlergear task close 3"
run "idlergear task close 4"
run "idlergear task close 5"
run "idlergear task close 6"
run "idlergear task close 7"

step "Listing task status..."
run "idlergear task list --state all"

# -----------------------------------------------------------------------------
# Step 8: Check Project Structure
# -----------------------------------------------------------------------------
header "Step 8: Verify Project Structure"

step "Running structure check..."
run "idlergear check --structure"

step "Checking for misplaced files..."
run "idlergear check --files || true"  # AGENTS.md is intentionally created for other AI tools

step "Getting project context (what AI would see)..."
run "idlergear context"

step "Showing /context slash command (for Claude Code)..."
echo -e "${BLUE}  ℹ A /context slash command was created automatically:${NC}"
run "cat .claude/commands/context.md"

# -----------------------------------------------------------------------------
# Step 9: GitHub Backend Configuration
# -----------------------------------------------------------------------------
header "Step 9: GitHub Backend (Optional)"

echo "To sync with GitHub Issues, you would run:"
echo ""
echo -e "${YELLOW}  # Auto-detect from git remote:${NC}"
echo -e "${YELLOW}  \$ idlergear setup-github${NC}"
echo ""
echo -e "${YELLOW}  # Or manually configure:${NC}"
echo -e "${YELLOW}  \$ idlergear config set github.repo owner/repo${NC}"
echo ""
echo "This enables:"
echo "  - idlergear task create --sync  (creates GitHub issue too)"
echo "  - idlergear sync                (sync local <-> GitHub)"
echo ""

# Check if we have a git remote
if git remote get-url origin 2>/dev/null; then
    info "Detected git remote: $(git remote get-url origin)"
    echo ""
    echo "You can run 'idlergear setup-github' to configure sync."
else
    info "No git remote yet. Add one with: git remote add origin <url>"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
header "Demo Complete!"

echo "Your 'Interesting Numbers' project has been created at:"
echo -e "${GREEN}  ${PROJECT_DIR}${NC}"
echo ""
echo "Project structure:"
echo ""
find . -type f \( -name "*.py" -o -name "*.toml" -o -name "*.md" -o -name "*.json" \) 2>/dev/null | grep -v __pycache__ | sort | head -20
echo ""
echo "IdlerGear knowledge:"
echo ""
echo "  Tasks:      $(idlergear task list --state all 2>/dev/null | wc -l) items"
echo "  Notes:      $(idlergear note list 2>/dev/null | wc -l) items"
echo "  References: $(idlergear reference list 2>/dev/null | wc -l) items"
echo ""
echo "Quick commands to try:"
echo ""
echo "  cd ${PROJECT_DIR}"
echo "  idlergear task list              # See open tasks"
echo "  idlergear task list --state all  # See all tasks"
echo "  idlergear task show 8            # View CLI task details"
echo "  idlergear vision show            # See project vision"
echo "  idlergear note list              # See development notes"
echo "  idlergear reference list         # See reference docs"
echo "  idlergear search 'prime'         # Search all knowledge"
echo "  idlergear context                # Get AI session context"
echo ""
echo "To run the code:"
echo ""
echo "  python src/interesting_numbers/numbers.py"
echo ""
echo -e "${GREEN}Happy coding!${NC}"
