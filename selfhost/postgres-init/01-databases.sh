#!/bin/bash
# Creates the two databases on first start. Docker runs this only when the data volume is empty.
# `lineup_app`, the role the API connects as, is not created here: the Alembic migration creates it
# and `lineup.db.selfhost_bootstrap` sets its password.
set -euo pipefail
psql -v ON_ERROR_STOP=1 -v auth_password="$AUTH_DB_PASSWORD" --username postgres <<'SQL'
CREATE DATABASE lineup;
CREATE DATABASE auth;
\connect auth
CREATE ROLE supabase_auth_admin LOGIN PASSWORD :'auth_password' NOINHERIT CREATEROLE;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
ALTER ROLE supabase_auth_admin SET search_path = auth;
SQL
