-- Migration 002: scope the semantic cache by policy and model.
--
-- Run once against a database created before this change (the startup script only
-- runs on first boot). Safe to re-run: ORA-01430 ("column already exists") is swallowed.
--
--   docker compose exec -T oracle-db sh -c \
--     'sqlplus -s system/"$ORACLE_PWD"@FREEPDB1' < scripts/migrate-002-cache-scope.sql

ALTER SESSION SET CONTAINER = FREEPDB1;

DECLARE
    column_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(column_exists, -01430);
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE semantic_cache ADD (scope_key VARCHAR2(64) DEFAULT '''' NOT NULL)';
EXCEPTION
    WHEN column_exists THEN NULL;
END;
/

CREATE INDEX IF NOT EXISTS idx_cache_scope ON semantic_cache (scope_key);

COMMIT;
