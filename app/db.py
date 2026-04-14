"""Oracle Database connection pool management."""

import os
from contextlib import contextmanager

import oracledb

# Connection config from environment
HOST = os.getenv("ORACLE_HOST", "localhost")
PORT = int(os.getenv("ORACLE_PORT", "1521"))
SERVICE = os.getenv("ORACLE_SERVICE", "FREEPDB1")
USER = os.getenv("ORACLE_USER", "system")
PASSWORD = os.getenv("ORACLE_PWD", "FreeP4ssw0rd!")

DSN = f"{HOST}:{PORT}/{SERVICE}"

# Module-level pool (initialized lazily)
_pool: oracledb.ConnectionPool | None = None


def get_pool() -> oracledb.ConnectionPool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=USER,
            password=PASSWORD,
            dsn=DSN,
            min=2,
            max=10,
            increment=1,
        )
    return _pool


def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection():
    """Get a connection from the pool (context manager)."""
    pool = get_pool()
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)


def check_health() -> dict:
    """Quick health check against the database."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM DUAL")
                cur.fetchone()
                return {"status": "healthy", "dsn": DSN}
    except Exception as e:
        return {"status": "unhealthy", "dsn": DSN, "error": str(e)}
