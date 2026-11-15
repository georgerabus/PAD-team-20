"""Check the replicated databases with the common Compose, in a disposable project.

Starts etcd and two clusters, applicant-db and player-db, from docker-compose.yml
with temporary passwords, and checks what the CPR README promises under
"Replicated databases": one primary and two replicas per cluster, the service's
user and database on port 5432, the db/<service>/ script run once, the read-only
user etl on port 5433, a failover that keeps every confirmed write, the old
primary back as a replica, a primary that carries on with both replicas down,
and one that stays primary while etcd is down.
Does not read the project's .env or touch an existing deployment.
"""

import argparse
import json
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CLUSTERS = ('applicant-db', 'player-db')
checks = []


def check(label, actual, expected):
    passed = actual == expected
    checks.append(passed)
    print(f'{"PASS" if passed else "FAIL"} {label}: {actual!r}', flush=True)
    if not passed:
        raise AssertionError(f'{label}: expected {expected!r}, received {actual!r}')


def wait_for(predicate, label, seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (subprocess.CalledProcessError, ValueError, KeyError):
            pass
        time.sleep(1)
    raise AssertionError(f'Timed out waiting for {label}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='georgerabus/pad-postgres-ha:1.0.1')
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='pad-postgres-ha-') as folder:
        project = Path(folder).name.lower()
        # Every variable Compose requires gets a value; only the databases' are used.
        required = sorted(set(re.findall(r'\$\{([A-Z_]+):\?', (ROOT / 'docker-compose.yml').read_text())))
        settings = {name: 'unused' for name in required}
        passwords = {name: secrets.token_hex(16) for name in ('APPLICANT_DB_PASSWORD', 'PLAYER_DB_PASSWORD', 'ETL_DB_PASSWORD')}
        settings.update(passwords, POSTGRES_HA_IMAGE=args.image)
        env_file = Path(folder) / '.env'
        env_file.write_text(''.join(f'{key}={value}\n' for key, value in settings.items()))
        command = ['docker', 'compose', '--project-directory', str(ROOT), '--env-file', str(env_file),
                   '-f', str(ROOT / 'docker-compose.yml'), '-p', project]

        def compose(*parts, timeout=300):
            return subprocess.run([*command, *parts], text=True, capture_output=True, timeout=timeout, check=True).stdout.strip()

        def sql(service, query, port=5432, user=None, database=None, password=None, timeout=30):
            # psql inside a cluster's HAProxy container, which has the service's user in its environment.
            env = []
            if user:
                env = ['-e', f'PGUSER={user}', '-e', f'PGPASSWORD={password}']
            if database:
                env += ['-e', f'PGDATABASE={database}']
            return compose('exec', '-T', *env, service, 'psql', '-h', '127.0.0.1', '-p', str(port), '-X', '-v',
                           'ON_ERROR_STOP=1', '-Atc', query, timeout=timeout)

        def members(cluster, through=1):
            listed = json.loads(compose('exec', '-T', f'{cluster}-{through}', 'patronictl', '-c', '/etc/patroni/patroni.yml',
                                        'list', '-f', 'json'))
            return {row['Member']: (row['Role'], row['State']) for row in listed}

        def leader(cluster, through=1):
            return next(name for name, (role, state) in members(cluster, through).items() if role == 'Leader' and state == 'running')

        def healthy(cluster, through=1):
            # One running leader, one streaming synchronous standby, one streaming replica.
            roles = sorted(role for role, state in members(cluster, through).values() if state in ('running', 'streaming'))
            return roles == ['Leader', 'Replica', 'Sync Standby']

        services = ['etcd-1', 'etcd-2', 'etcd-3'] + [f'{c}{n}' for c in CLUSTERS for n in ('', '-1', '-2', '-3')]
        try:
            started = time.monotonic()
            compose('up', '-d', '--pull', 'never', '--wait', '--wait-timeout', '300', *services, timeout=360)
            for cluster in CLUSTERS:
                wait_for(lambda: healthy(cluster), f'{cluster} streaming to both replicas', 120)
            print(f'Both clusters up in {time.monotonic() - started:.0f} s', flush=True)

            for cluster in CLUSTERS:
                check(f'{cluster} has a leader, a synchronous standby and a replica',
                      sorted(role for role, _ in members(cluster).values()), ['Leader', 'Replica', 'Sync Standby'])
            check('5432 is the primary, as the service\'s user, in its database',
                  sql('applicant-db', 'select current_user, current_database(), pg_is_in_recovery()'), 'applicant|applicant|f')
            check('the service\'s user can create its tables', sql('applicant-db', 'create table ha_check (id int primary key)'),
                  'CREATE TABLE')

            tables = sorted(re.findall(r'(?i)create table if not exists (\w+)', (ROOT / 'db/player/schema.sql').read_text()))
            listed = "select string_agg(tablename, ',' order by tablename) from pg_tables where schemaname = 'public'"
            check('the db/player/ script ran once, as the service\'s user', sql('player-db',
                  "select string_agg(distinct tableowner, ',') || ':' || count(*) from pg_tables where schemaname = 'public'"),
                  f'player:{len(tables)}')
            etl = {'user': 'etl', 'password': passwords['ETL_DB_PASSWORD']}
            check('etl reads the same tables on 5433, a replica', sql('player-db', f'select pg_is_in_recovery(); {listed}',
                  port=5433, database='player', **etl), 't\n' + ','.join(tables))
            refused = subprocess.run([*command, 'exec', '-T', '-e', 'PGUSER=etl', '-e', f'PGPASSWORD={etl["password"]}',
                                      'applicant-db', 'psql', '-h', '127.0.0.1', '-X', '-Atc', 'insert into ha_check values (0)'],
                                     text=True, capture_output=True, timeout=30)
            check('etl cannot write, even on the primary', 'read-only transaction' in refused.stderr, True)

            # Failover: the primary dies without a word. Every write it confirmed
            # was on the synchronous standby too, so none is lost.
            sql('applicant-db', 'insert into ha_check select generate_series(1, 100)')
            old = leader('applicant-db')
            survivor = next(n for n in (1, 2, 3) if f'applicant-db-{n}' != old)
            killed = time.monotonic()
            compose('kill', old)
            new = wait_for(lambda: (lambda name: name if name != old else None)(leader('applicant-db', survivor)),
                           'a new primary', 90)
            wait_for(lambda: sql('applicant-db', 'select pg_is_in_recovery()', timeout=5) == 'f', 'HAProxy on the new primary', 60)
            seconds = time.monotonic() - killed
            print(f'{new} took over {seconds:.1f} s after {old} was killed', flush=True)
            check('a replica takes over within 40 s', seconds < 40, True)
            check('no confirmed write is lost', sql('applicant-db', 'select count(*) from ha_check'), '100')
            check('5432 writes again', sql('applicant-db', 'insert into ha_check values (101)'), 'INSERT 0 1')
            compose('start', old)
            wait_for(lambda: members('applicant-db', survivor).get(old, ('', ''))[1] == 'streaming', f'{old} streaming again', 120)
            check('the old primary is back as a replica', members('applicant-db', survivor)[old][0] in ('Replica', 'Sync Standby'), True)
            wait_for(lambda: sql('applicant-db', 'select count(*) from ha_check', port=5433, database='applicant', **etl,
                                 timeout=5) == '101', 'the replicas caught up', 60)

            # With both replicas down, the primary carries on alone.
            replicas = [f'applicant-db-{n}' for n in (1, 2, 3) if f'applicant-db-{n}' != new]
            compose('kill', *replicas)
            alone = time.monotonic()
            check('with both replicas down, the primary still commits',
                  sql('applicant-db', 'insert into ha_check values (102)', timeout=60), 'INSERT 0 1')
            print(f'The first commit alone took {time.monotonic() - alone:.1f} s', flush=True)
            compose('start', *replicas)
            survivor = int(new.rsplit('-', 1)[1])
            wait_for(lambda: healthy('applicant-db', survivor), 'both replicas streaming again', 120)
            check('both replicas are back and in sync', sql('applicant-db', 'select count(*) from ha_check', port=5433,
                  database='applicant', **etl), '102')

            # With etcd gone, the primary still reaches both replicas, so it
            # stays primary (failsafe mode) well past the 20 s ttl.
            primary = leader('applicant-db', survivor)
            compose('stop', 'etcd-1', 'etcd-2', 'etcd-3')
            time.sleep(30)
            check('with every etcd node stopped for 30 s, the primary still commits',
                  sql('applicant-db', 'insert into ha_check values (103)', timeout=30), 'INSERT 0 1')
            compose('start', 'etcd-1', 'etcd-2', 'etcd-3')
            wait_for(lambda: healthy('applicant-db', survivor), 'the cluster back on etcd', 120)
            check('and it is still the same primary', leader('applicant-db', survivor), primary)

            stats = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}',
                                    *json_names(compose('ps', '--format', 'json'))], text=True, capture_output=True).stdout
            print('docker stats:\n' + stats, flush=True)
            print(f'All {len(checks)} replicated-database checks passed.')
        except Exception as error:
            print(getattr(error, 'stderr', None) or '', flush=True)
            print(compose('ps', '--all'))
            for service in services:
                print(f'--- {service}\n' + subprocess.run([*command, 'logs', '--no-color', '--tail', '20', service],
                                                         text=True, capture_output=True).stdout)
            raise
        finally:
            subprocess.run([*command, 'down', '-v', '--remove-orphans'], capture_output=True, timeout=300)
    print('Disposable resources removed.')


def json_names(output):
    rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    return [row['Name'] for row in rows]


if __name__ == '__main__':
    main()
