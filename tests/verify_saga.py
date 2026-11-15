"""Check the saga that creates an applicant end to end, with the real services (Lab 5).

Starts disposable containers: Service Discovery, the Message Broker with its
saga coordinator, Applicant and Credential, each with its own PostgreSQL, and
University Record: the real image with --records-image, otherwise a stand-in
(tests/fixtures/participant_standin.py). Session's CreateApplicant goes to the
broker's POST /messages, as Session sends it. Checked against each service's
database, as the CPR README's "Creating an applicant across three databases"
promises:

- a saga that completes keeps the applicant in every service;
- one that University Record refuses undoes Credential's slice (stand-in only);
- one whose University Record is down past the retries is compensated once it
  is back, its own step first;
- one whose Credential database is down for a while still completes;
- every service then keeps the same applicants.

Uses disposable credentials, without reading the project's .env.
"""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
checks = []
containers = []


def docker(*args, timeout=120):
    result = subprocess.run(['docker', *args], text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def check(label, actual, expected):
    passed = actual == expected
    checks.append(passed)
    shown = repr(actual) if len(repr(actual)) <= 140 else repr(actual)[:137] + '...'
    print(f'{"PASS" if passed else "FAIL"} {label}: {shown}', flush=True)
    if not passed:
        raise AssertionError(f'{label}: expected {expected!r}, received {actual!r}')


def wait_for(predicate, label, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (OSError, ValueError, RuntimeError, KeyError):
            pass
        time.sleep(1)
    raise TimeoutError(f'{label} did not happen within {seconds} s')


def call(base, path, method='GET', body=None, timeout=20):
    request = urllib.request.Request(base + path, method=method, headers={'Content-Type': 'application/json'},
        data=None if body is None else json.dumps(body).encode())
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read().decode()
        try:
            return response.status, json.loads(raw)
        except ValueError:
            return response.status, raw


def published(container, port):
    return 'http://' + docker('port', container, port).splitlines()[0].replace('0.0.0.0', '127.0.0.1')


def timestamp(moment):
    return moment.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def step_id(saga_id, name):
    """The messageId the coordinator gives call `name` (`1:do`, `2:undo`) of a saga."""
    return str(uuid.uuid5(uuid.UUID(saga_id), name))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--applicant-image', default='georgerabus/pad-applicant-service:5.0.0-rc.1')
    parser.add_argument('--credential-image', default='georgerabus/pad-credential-service:5.0.0-rc.1')
    parser.add_argument('--broker-image', default='georgerabus/pad-message-broker:5.0.0-rc.1')
    parser.add_argument('--discovery-image', default='georgerabus/pad-service-discovery:4.0.0')
    parser.add_argument('--records-image', help='the real University Record; a stand-in when left out')
    parser.add_argument('--postgres-image', default='postgres:17')
    parser.add_argument('--python-image', default='python:3.13-slim')
    args = parser.parse_args()
    real_records = args.records_image is not None
    network = 'pad-saga-' + uuid.uuid4().hex[:10]
    docker('network', 'create', network)
    try:
        def run(label, *options):
            name = f'{network}-{label}'
            docker('run', '-d', '--name', name, '--network', network, '--network-alias', label, *options)
            containers.append(name)
            return name

        databases = {}

        def database(label, name):
            password = secrets.token_hex(24)
            databases[label] = (run(label, '-e', f'POSTGRES_DB={name}', '-e', f'POSTGRES_USER={name}',
                '-e', f'POSTGRES_PASSWORD={password}', args.postgres_image), name)
            return password

        def ready(label):
            container, name = databases[label]
            wait_for(lambda: subprocess.run(['docker', 'exec', container, 'pg_isready', '-h', '127.0.0.1',
                '-U', name, '-d', name], capture_output=True).returncode == 0, f'{label} accepting connections')

        def sql(label, query):
            container, name = databases[label]
            return docker('exec', container, 'psql', '-U', name, '-d', name, '-Atc', query)

        passwords = {'applicant': database('applicant-db', 'applicant'),
            'credential': database('credential-db', 'credential')}
        if real_records:
            passwords['records'] = database('records-db', 'university_record')
        discovery_env = ('-e', 'SERVICE_DISCOVERY_URL=http://service-discovery:8000')
        discovery = run('service-discovery', '-p', '127.0.0.1::8000', '-e', 'HEALTH_CHECK_INTERVAL_SECONDS=1',
            args.discovery_image)
        broker = run('broker', '-p', '127.0.0.1::8000', *discovery_env, args.broker_image)
        for label in databases:
            ready(label)
        run('credential', *discovery_env, '-e', 'DB_HOST=credential-db', '-e', 'DB_DATABASE=credential',
            '-e', 'DB_USERNAME=credential', '-e', 'DB_PASSWORD=' + passwords['credential'],
            '-e', 'CREDENTIAL_ISSUER_SECRET=' + secrets.token_hex(32), '-e', 'HANDOVER_TARGETS=',
            '-e', 'BROKER_GRPC_ADDRESS=broker:9001', args.credential_image)
        applicant = run('applicant', '-p', '127.0.0.1::80', *discovery_env, '-e', 'DB_HOST=applicant-db',
            '-e', 'DB_DATABASE=applicant', '-e', 'DB_USERNAME=applicant', '-e', 'DB_PASSWORD=' + passwords['applicant'],
            '-e', 'BROKER_URL=http://broker:8000', '-e', 'HANDOVER_TARGETS=credential,records',
            '-e', 'BROKER_GRPC_ADDRESS=broker:9001', args.applicant_image)
        if real_records:
            records = run('records', *discovery_env, '-e', 'SD_SERVICE_NAME=records', '-e', 'APP_ENV=production',
                '-e', 'APP_DEBUG=false', '-e', 'APP_KEY=base64:' + base64.b64encode(secrets.token_bytes(32)).decode(),
                '-e', 'LOG_CHANNEL=stderr', '-e', 'DB_CONNECTION=pgsql', '-e', 'DB_HOST=records-db', '-e', 'DB_PORT=5432',
                '-e', 'DB_DATABASE=university_record', '-e', 'DB_USERNAME=university_record',
                '-e', 'DB_PASSWORD=' + passwords['records'], '-e', 'SESSION_DRIVER=array', '-e', 'CACHE_STORE=file',
                '-e', 'QUEUE_CONNECTION=sync', args.records_image)
        else:
            records = run('records', '-p', '127.0.0.1::8000', *discovery_env, '-e', 'REGISTER_AS=records',
                '-v', f'{ROOT / "tests/fixtures/participant_standin.py"}:/standin.py:ro',
                args.python_image, 'python', '-u', '/standin.py')
        sd, broker_url, applicant_url = (published(discovery, '8000/tcp'), published(broker, '8000/tcp'),
            published(applicant, '80/tcp'))
        for name in ('applicant', 'credential', 'records'):
            wait_for(lambda: call(sd, f'/services/{name}')[1].get('instances'), f'{name} registered', 240)
        print(f'University Record: {args.records_image or "the stand-in"}', flush=True)

        session_id = str(uuid.uuid4())

        def create(seconds=10):
            message = {'messageId': str(uuid.uuid4()), 'kind': 'request', 'source': 'session', 'target': 'applicant',
                'operation': 'CreateApplicant', 'identity': None, 'payload': {'sessionId': session_id},
                'deadline': timestamp(datetime.now(timezone.utc) + timedelta(seconds=seconds))}
            status, reply = call(broker_url, '/messages', 'POST', message, timeout=seconds + 5)
            if status != 200:
                raise AssertionError(f'POST /messages answered {status}: {reply}')
            return reply['status'], reply['payload']

        def saga(saga_id):
            return call(broker_url, f'/sagas/{saga_id}')[1]

        def saga_logged(pattern):
            with urllib.request.urlopen(f'{applicant_url}/logs?level=log', timeout=5) as response:
                lines = [json.loads(line) for line in response.read().decode().splitlines() if line.strip()]
            return [match for match in (re.match(pattern, line.get('message', ''))
                for line in lines if line.get('context') == 'Saga') if match]

        def standin():
            return call(published(records, '8000/tcp'), '/recorded')[1]

        def kept(applicant_id):
            here = {'applicant': int(sql('applicant-db', f"select count(*) from applicants where applicant_id = '{applicant_id}'")),
                'credential': int(sql('credential-db', f"select count(*) from applicants where applicant_id = '{applicant_id}'"))}
            if real_records:
                here['records'] = int(sql('records-db',
                    f"select count(*) from applicant_records where applicant_id = '{applicant_id}'"))
            else:
                here['records'] = int(applicant_id in standin()['kept'])
            return here

        def handled(label, message_id):
            row = sql(label, f"select status, payload from handled_messages where message_id = '{message_id}'")
            if not row:
                return None
            status, payload = row.split('|', 1)
            return int(status), json.loads(payload) if payload else None

        def records_handled(message_id):
            """University Record's reply to one message: its own record, or what the stand-in received."""
            if real_records:
                return handled('records-db', message_id)
            return [delivery['operation'] for delivery in standin()['deliveries'] if delivery['messageId'] == message_id]

        everywhere = {'applicant': 1, 'credential': 1, 'records': 1}
        nowhere = {'applicant': 0, 'credential': 0, 'records': 0}

        # 1. A saga that completes.
        status, payload = create()
        applicant_id = payload.get('applicantId')
        if status != 201:
            for match in saga_logged(r'^Saga .*'):
                print('  Applicant logged:', match.group(0), flush=True)
        check('Session\'s CreateApplicant answers 201 once the saga completes', status, 201)
        [match] = saga_logged(rf'^Saga (\S+) created applicant {applicant_id} in every service$')
        saga_id = match.group(1)
        view = saga(saga_id)
        check('the broker has it completed, steps in the README\'s order', (view['state'],
            [(step['service'], step['state']) for step in view['steps']]),
            ('completed', [('credential', 'done'), ('records', 'done'), ('applicant', 'done')]))
        check('every service keeps the applicant', kept(applicant_id), everywhere)
        stored = handled('credential-db', step_id(saga_id, '1:do'))
        check('Credential applied step 1 once, under its step ID', (stored[0], stored[1].get('applicantId')),
            (201, applicant_id))
        stored = records_handled(step_id(saga_id, '2:do'))
        check('University Record got step 2, under its step ID',
            (stored[0], stored[1].get('applicantId')) if real_records else stored,
            (201, applicant_id) if real_records else ['CreateApplicant'])

        # 2. University Record refuses: Credential's slice is undone.
        if not real_records:
            call(published(records, '8000/tcp'), '/mode', 'POST', {'refuse': 'CreateApplicant'})
            status, payload = create()
            call(published(records, '8000/tcp'), '/mode', 'POST', {'refuse': None})
            check('a step University Record refuses answers 502 PEER_UNAVAILABLE', (status, payload.get('error')),
                (502, 'PEER_UNAVAILABLE'))
            [match] = saga_logged(r'^Saga (\S+) was compensated, so applicant (\S+) is kept nowhere')
            refused_saga, refused = match.groups()
            view = saga(refused_saga)
            check('the broker has it compensated', (view['state'], view['steps'][0]['state']),
                ('compensated', 'compensated'))
            check('Credential\'s slice is undone by DeleteApplicant, under step 1\'s undo ID',
                handled('credential-db', step_id(refused_saga, '1:undo')), (200, {'applicantId': refused, 'deleted': True}))
            check('and no service keeps the applicant', kept(refused), nowhere)

        # 3. University Record is down past the retries.
        docker('stop', records)
        wait_for(lambda: not call(sd, '/services/records')[1].get('instances'), 'records out of Service Discovery', 60)
        status, payload = create(seconds=12)
        check('with University Record down, Applicant answers 202 and where to follow the saga',
            (status, sorted(payload)), (202, ['applicantId', 'statusPath']))
        down, path = payload['applicantId'], payload['statusPath']
        down_saga = path.rsplit('/', 1)[1]
        wait_for(lambda: call(broker_url, path)[1].get('state') == 'compensating',
            'the step to fail after 30 s of retries', 120)
        check('until the step is given up, Credential keeps its slice',
            sql('credential-db', f"select count(*) from applicants where applicant_id = '{down}'"), '1')
        docker('start', records)
        wait_for(lambda: call(broker_url, path)[1].get('state') == 'compensated',
            'the compensations once University Record is back', 180)
        stored = records_handled(step_id(down_saga, '2:undo'))
        check('University Record\'s own step is undone first, though it never arrived', stored,
            (200, {'applicantId': down, 'deleted': False}) if real_records else ['DeleteApplicant'])
        check('then Credential\'s, by DeleteApplicant', handled('credential-db', step_id(down_saga, '1:undo')),
            (200, {'applicantId': down, 'deleted': True}))
        check('and no service keeps the applicant', kept(down), nowhere)

        # 4. Credential's database is down for a while.
        credential_db = databases['credential-db'][0]
        docker('stop', credential_db)
        started = time.monotonic()
        status, payload = create(seconds=12)
        check('with Credential\'s database down, Applicant answers 202', status, 202)
        slow, path = payload['applicantId'], payload['statusPath']
        time.sleep(max(0.0, 8 - (time.monotonic() - started)))
        docker('start', credential_db)
        ready('credential-db')
        wait_for(lambda: call(broker_url, path)[1].get('state') == 'completed',
            'the saga to complete once the database is back', 60)
        first = call(broker_url, path)[1]['steps'][0]
        check('Credential\'s step was tried again until the database answered', (first['state'], first['attempts'] > 1),
            ('done', True))
        check('and every service keeps the applicant', kept(slow), everywhere)

        # 5. All or nothing: the same applicants everywhere.
        applicants = sql('applicant-db', 'select applicant_id from applicants order by 1').split()
        same = {'credential': sql('credential-db', 'select applicant_id from applicants order by 1').split() == applicants}
        if real_records:
            same['records'] = sql('records-db', 'select applicant_id from applicant_records order by 1').split() == applicants
        check(f'every service keeps the same {len(applicants)} applicants', all(same.values()), True)

        print(f'All {len(checks)} saga checks passed.')
    finally:
        for name in reversed(containers):
            subprocess.run(['docker', 'rm', '-f', '-v', name], capture_output=True)
        subprocess.run(['docker', 'network', 'rm', network], capture_output=True)
    print('Disposable resources removed.')


if __name__ == '__main__':
    main()
