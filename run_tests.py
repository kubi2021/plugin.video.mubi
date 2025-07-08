#!/usr/bin/env python3
"""
Test runner script for the MUBI Kodi plugin.

This script provides a convenient way to run tests with proper configuration
and reporting.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed!")
        print(f"Return code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"ERROR: Command not found. Make sure the required tools are installed.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for MUBI Kodi plugin")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", "-n", type=int, help="Run tests in parallel")
    parser.add_argument("--test-file", help="Run specific test file")
    parser.add_argument("--test-function", help="Run specific test function")
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = True
    
    # Install dependencies if requested
    if args.install_deps:
        cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"]
        success &= run_command(cmd, "Installing test dependencies")
        if not success:
            return 1
    
    # Format code if requested
    if args.format:
        # Run black
        cmd = [sys.executable, "-m", "black", "resources/", "tests/", "addon.py"]
        run_command(cmd, "Formatting code with black")
        
        # Run isort
        cmd = [sys.executable, "-m", "isort", "resources/", "tests/", "addon.py"]
        run_command(cmd, "Sorting imports with isort")
    
    # Run linting if requested
    if args.lint:
        cmd = [sys.executable, "-m", "flake8", "resources/", "tests/", "addon.py"]
        success &= run_command(cmd, "Running flake8 linting")
    
    # Build pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]
    
    if args.verbose:
        pytest_cmd.append("-v")
    
    if args.parallel:
        pytest_cmd.extend(["-n", str(args.parallel)])
    
    if args.coverage:
        pytest_cmd.extend([
            "--cov=resources",
            "--cov=addon",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    if args.test_file:
        pytest_cmd.append(f"tests/{args.test_file}")
    elif args.test_function:
        pytest_cmd.extend(["-k", args.test_function])
    else:
        pytest_cmd.append("tests/")
    
    # Run tests
    success &= run_command(pytest_cmd, "Running tests")
    
    if success:
        print("\n" + "="*60)
        print("✅ All operations completed successfully!")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ Some operations failed!")
        print("="*60)
        return 1


if __name__ == "__main__":
    import os
    sys.exit(main())
