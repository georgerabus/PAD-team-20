-- The database and its user are created when its Patroni cluster is (docker/postgres-ha/pad-post-bootstrap).
-- Laravel migrations create the tables when the credential service starts; no sample data is inserted.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
