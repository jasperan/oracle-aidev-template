#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "Starting Oracle 26ai Free container..."
docker compose up -d oracle-db

echo ""
echo "Waiting for database to become healthy (2-5 minutes on first run)..."
echo ""

until [ "$(docker inspect -f '{{.State.Health.Status}}' oracle-aidev-db 2>/dev/null)" = "healthy" ]; do
    status=$(docker inspect -f '{{.State.Health.Status}}' oracle-aidev-db 2>/dev/null || echo "starting")
    printf "\r  Status: %-20s" "$status"
    sleep 5
done

HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo ""
echo "=========================================="
echo "  Oracle 26ai Free is READY"
echo "=========================================="
echo ""
echo "  Local:     localhost:1521/FREEPDB1"
echo "  Remote:    ${HOST_IP}:1521/FREEPDB1"
echo "  User:      system"
echo "  Password:  (see .env file)"
echo ""
echo "  Python:"
echo "    import oracledb"
echo "    conn = oracledb.connect(user='system', password='...', dsn='localhost:1521/FREEPDB1')"
echo ""
echo "  sqlplus:"
echo "    docker exec -it oracle-aidev-db sqlplus system/\${ORACLE_PWD}@FREEPDB1"
echo ""
echo "=========================================="
