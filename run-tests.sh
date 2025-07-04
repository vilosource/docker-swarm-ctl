#!/bin/bash

# Exit on error
set -e

echo "Starting Docker Compose services..."
docker compose up -d

echo "Waiting for services to be ready..."
# Wait for backend to be healthy
timeout 60 bash -c 'until curl -f http://localhost/api/v1/health > /dev/null 2>&1; do sleep 1; done'

echo "Initializing database..."
docker compose exec -T backend python scripts/init_db.py

echo "Installing Playwright..."
npm install -g @playwright/test
playwright install chromium

echo "Running Playwright tests..."
playwright test

echo "Tests completed!"