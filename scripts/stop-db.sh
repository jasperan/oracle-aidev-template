#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "Stopping Oracle 26ai Free container..."
docker compose down

echo "Database stopped. Data is preserved in the oracle-data volume."
echo "To remove data: docker volume rm oracle-aidev-template_oracle-data"
