#!/bin/bash
# Setup script for MUBI plugin test environment

set -e

echo "🚀 Setting up MUBI Plugin Test Environment"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment (local only, not synced to git)..."
    python3 -m venv venv
    echo "✅ Virtual environment created in ./venv/"
    echo "ℹ️  Note: venv/ directory is excluded from git via .gitignore"
else
    echo "✅ Virtual environment already exists in ./venv/"
fi

# Activate virtual environment and install requirements
echo "📋 Installing test requirements..."
./venv/bin/pip install -r requirements-test.txt

echo ""
echo "🎯 Test Environment Setup Complete!"
echo "=================================="
echo ""
echo "To use the test environment:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run tests:"
echo "   pytest tests/                    # Run all tests"
echo "   pytest tests/ -m security        # Run security tests only"
echo "   pytest tests/ -m stress          # Run stress tests only"
echo "   pytest tests/ -m integration     # Run integration tests only"
echo "   pytest tests/ -m e2e             # Run end-to-end tests only"
echo "   pytest tests/ -m quality         # Run quality framework tests only"
echo ""
echo "3. Run with coverage:"
echo "   pytest tests/ --cov=resources/lib --cov-report=html"
echo ""
echo "4. Run test discovery validation:"
echo "   python tests/test_discovery.py"
echo ""
echo "5. Run enterprise test runner:"
echo "   python tests/test_runner_enterprise.py"
echo ""
echo "📊 Current test status:"
./venv/bin/python -m pytest --collect-only tests/ -q | grep "collected"
echo ""
echo "🎉 Ready to test!"
