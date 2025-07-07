#!/bin/bash

# Run all tests with coverage report

echo "Running backend tests..."
echo "========================"

# Unit tests
echo -e "\n1. Running unit tests..."
python -m pytest tests/unit/ -v --tb=short

# Integration tests (if database is available)
echo -e "\n2. Running integration tests..."
python -m pytest tests/integration/ -v --tb=short -m "not slow"

# Coverage report
echo -e "\n3. Generating coverage report..."
python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

echo -e "\nTests completed!"
echo "Coverage report available at: htmlcov/index.html"