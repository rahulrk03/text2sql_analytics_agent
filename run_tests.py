#!/usr/bin/env python3
"""
Simple test runner script for the text2sql analytics agent.
"""

import subprocess
import sys


def run_tests():
    """Run all tests and return the exit code."""
    try:
        print("Running unit tests for API endpoints...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            check=False,
            capture_output=False
        )
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    sys.exit(exit_code)