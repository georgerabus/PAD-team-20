#!/bin/sh
# Runs once, on the warehouse's first start with an empty volume: creates the
# user Grafana reads the warehouse with. It may read every table the ETL
# creates, now and later, and change none of them.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v reader_password="$WAREHOUSE_GRAFANA_PASSWORD" <<'SQL'
CREATE ROLE grafana_reader LOGIN PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE warehouse TO grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;
-- The ETL creates the tables after this runs, as the warehouse's owner.
ALTER DEFAULT PRIVILEGES FOR ROLE warehouse IN SCHEMA public
  GRANT SELECT ON TABLES TO grafana_reader;
SQL
