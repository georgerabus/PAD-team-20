# PostgreSQL 17 run by Patroni, one image for every node of every cluster, and
# for the HAProxy in front of each cluster, which then has psql to check it.
# Patroni comes from the PGDG repository the postgres image already uses, and
# HAProxy from Debian.
FROM postgres:17.12-trixie

RUN apt-get update \
    && apt-get install -y --no-install-recommends patroni python3-etcd haproxy \
    && rm -rf /var/lib/apt/lists/*

COPY patroni.yml /etc/patroni/patroni.yml
COPY haproxy.cfg /etc/haproxy/pad.cfg
COPY pad-patroni pad-post-bootstrap /usr/local/bin/

USER postgres
EXPOSE 5432 5433 8008
ENTRYPOINT ["pad-patroni"]
