#!/usr/bin/env bash
# Waits for Oracle DB to be healthy. Used by CI and app startup.
set -euo pipefail

CONTAINER="${1:-oracle-aidev-db}"
TIMEOUT="${2:-300}"

echo "Waiting up to ${TIMEOUT}s for ${CONTAINER} to be healthy..."

elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    status=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "not_found")
    if [ "$status" = "healthy" ]; then
        echo "Database is healthy after ${elapsed}s."
        exit 0
    fi
    printf "\r  [%3ds] Status: %-20s" "$elapsed" "$status"
    sleep 5
    elapsed=$((elapsed + 5))
done

echo ""
echo "ERROR: Database did not become healthy within ${TIMEOUT}s"
exit 1
