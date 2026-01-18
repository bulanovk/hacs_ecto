#!/bin/bash
# Test runner script for Ectocontrol Modbus Integration

set -e

echo "=========================================="
echo "Ectocontrol Modbus Integration Test Runner"
echo "=========================================="
echo ""

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  WARNING: Not in a virtual environment"
    echo "   It's recommended to activate venv first:"
    echo "   source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if socat is available for integration tests
if ! command -v socat &> /dev/null; then
    echo "⚠️  WARNING: socat is not installed"
    echo "   Integration tests with PTY will be skipped"
    echo "   Install with: sudo apt-get install socat"
    echo ""
    SOCAT_AVAILABLE=false
else
    echo "✓ socat found - integration tests enabled"
    SOCAT_AVAILABLE=true
fi

# Run tests
echo "Running tests..."
echo ""

if [ "$SOCAT_AVAILABLE" = true ]; then
    # Run all tests including integration tests
    pytest \
        --cov=custom_components/ecto_modbus \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --cov-report=xml \
        -v \
        --tb=short \
        "$@"
else
    # Skip integration tests if socat is not available
    pytest \
        --cov=custom_components/ecto_modbus \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --cov-report=xml \
        -v \
        --tb=short \
        -m "not integration" \
        "$@"
fi

echo ""
echo "=========================================="
echo "Test run completed!"
echo ""
echo "Coverage report:"
echo "  HTML: htmlcov/index.html"
echo "  XML:  coverage.xml"
echo "=========================================="
