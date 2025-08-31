#!/bin/bash
# Helper script to activate the virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo "✅ Virtual environment activated"
    echo "Python: $(which python)"
    echo "Version: $(python --version)"
else
    echo "❌ Virtual environment not found!"
    echo "Please run: python3.11 -m venv .venv"
fi