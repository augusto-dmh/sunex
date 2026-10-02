#!/usr/bin/env bash
# Runs once, when the pgsql container initialises an empty data directory.
# Creates the database the test suite uses, so tests never touch development data.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    SELECT 'CREATE DATABASE "${TESTING_DB_DATABASE}"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${TESTING_DB_DATABASE}')\gexec
SQL
