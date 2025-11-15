#!/bin/bash
set -e

# --- IdlerGear Run Script ---
# This script is managed by IdlerGear to provide a consistent
# entry point for running and testing the project.

# 1. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# 2. Install Dependencies
pip install pip-tools --quiet
pip-compile requirements.in --quiet
pip-sync --quiet

# 3. Run Code Quality Checks and Tests
echo "Running Black formatter..."
python -m black src/ --check --diff || { echo "Black formatting issues found. Run 'python -m black src/' to fix."; exit 1; }

echo "Running Ruff linter..."
python -m ruff check src/ || { echo "Ruff linting issues found."; exit 1; }

echo "Running Pytest tests with Coverage..."
python -m pytest --cov=src --cov-report=term-missing || { echo "Tests failed or coverage issues found."; exit 1; }

# 4. Run the Application
# Pass all arguments from run.sh to the python script
python src/main.py "$@"
