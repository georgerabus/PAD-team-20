"""Check the common Compose with a fresh, disposable project and real services.

Uses temporary credentials, signing keys, volumes and loopback ports. Does not
read the project's .env or alter an existing Compose deployment. Failures in
rules/records, Session's outgoing calls or event delivery remain failures;
successful container startup alone is not a complete integration result.
"""

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.error
from urllib.parse import urlsplit
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
HTTP_CLIENT = """
import json,sys,urllib.error,urllib.request
d=json.loads(sys.argv[1])
r=urllib.request.Request('http://127.0.0.1:8001'+d['path'],
    data=None if d['body'] is None else json.dumps(d['body']).encode(),
    method=d['method'],headers=d['headers'])
try: response=urllib.request.urlopen(r,timeout=20)
except urllib.error.HTTPError as error: response=error
with response: print(json.dumps([response.status,response.read().decode()]))
"""


def run(command, input=None, timeout=180):
    result = subprocess.run(command, input=input, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def decode(body):
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return body


def call(url, method='GET', body=None, headers=None):
    headers = dict(headers or {})
    if body is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, decode(response.read().decode())


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def websocket_status(port, path):
    with socket.create_connection(('127.0.0.1', port), timeout=10) as sock:
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        request = (f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
                   'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                   f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
        sock.sendall(request.encode())
        return int(sock.recv(4096).split(b'\r\n', 1)[0].split()[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gateway-image', required=True)
    parser.add_argument('--rules-image', required=True)
    parser.add_argument('--records-image', required=True)
    parser.add_argument('--session-image', default='catalinasiminiuc/pad-server-moderation-session-service:2.0.1')
    parser.add_argument('--applicant-image', default='georgerabus/pad-applicant-service:2.0.0-rc.1')
    parser.add_argument('--credential-image', default='georgerabus/pad-credential-service:2.0.0-rc.1')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    checks = []

    def check(label, actual, expected):
        passed = actual == expected
        checks.append({'check': label, 'passed': passed, 'actual': actual, 'expected': expected})
        print(f'  {"ok" if passed else "FAIL"}  {label}: {actual!r}', flush=True)
        return passed

    with tempfile.TemporaryDirectory(prefix='pad-compose-check-') as folder:
        work = Path(folder)
        project = work.name
        keys = work / 'keys'
        for issuer in ('player', 'session'):
            directory = keys / issuer
            directory.mkdir(parents=True)
            subprocess.run(['openssl', 'genrsa', '-out', str(directory / 'private.pem'), '2048'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['openssl', 'rsa', '-in', str(directory / 'private.pem'), '-pubout',
                            '-out', str(directory / 'public.pem')],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (directory / 'private.pem').chmod(0o644)

        ports = [free_port() for _ in range(3)]
        settings = {
            'GATEWAY_IMAGE': args.gateway_image, 'SERVER_RULES_IMAGE': args.rules_image,
            'UNIVERSITY_RECORD_IMAGE': args.records_image, 'SESSION_IMAGE': args.session_image,
            'APPLICANT_IMAGE': args.applicant_image, 'CREDENTIAL_IMAGE': args.credential_image,
            'GATEWAY_HTTP_PORT': str(ports[0]), 'SESSION_WS_PORT': str(ports[1]), 'DM_WS_PORT': str(ports[2]),
            'SESSION_PUBLIC_WS_BASE_URL': f'ws://127.0.0.1:{ports[1]}',
            'DM_PUBLIC_WS_BASE_URL': f'ws://127.0.0.1:{ports[2]}',
            'PAD_KEYS_DIR': str(keys), 'CREDENTIAL_ISSUER_SECRET': secrets.token_hex(32),
            'SERVER_RULES_APP_KEY': 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode(),
            'UNIVERSITY_RECORD_APP_KEY': 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode(),
        }
        for service in ('PLAYER', 'SESSION', 'DM', 'MODERATION', 'SERVER_RULES', 'UNIVERSITY_RECORD', 'APPLICANT', 'CREDENTIAL'):
            settings[service + '_DB_PASSWORD'] = secrets.token_hex(24)
        env_file = work / '.env'
        env_file.write_text(''.join(f'{key}={value}\n' for key, value in settings.items()))
        command = ['docker', 'compose', '--project-directory', str(ROOT), '--env-file', str(env_file),
                   '-f', str(ROOT / 'docker-compose.yml'), '-p', project]

        def compose(*parts, input=None):
            return run([*command, *parts], input=input)

        def internal(path, method='GET', body=None, headers=None):
            headers = dict(headers or {})
            if body is not None:
                headers['Content-Type'] = 'application/json'
            status, raw = json.loads(compose('exec', '-T', 'gateway', 'python', '-c', HTTP_CLIENT,
                json.dumps({'path': path, 'method': method, 'body': body, 'headers': headers})))
            return status, decode(raw)

        public = f'http://127.0.0.1:{ports[0]}'
        try:
            config = json.loads(compose('config', '--format', 'json'))
            published = sorted(name for name, service in config['services'].items() if service.get('ports'))
            check('only Gateway and WS edge publish ports', published, ['gateway', 'ws-edge'])
            check('Gateway publishes only its public listener',
                  [p['target'] for p in config['services']['gateway']['ports']], [8000])
            check('Player calls Session through internal Gateway',
                  config['services']['player']['environment']['SESSION_BASE_URL'], 'http://gateway:8001/session')
            print('Starting disposable common Compose project...', flush=True)
            try:
                compose('up', '-d', '--wait', '--wait-timeout', '120')
            except RuntimeError:
                # Preserve startup diagnostics before disposable resources are
                # removed. Startup logs contain no test accounts or tokens.
                for row in compose('ps', '--all', '--format', 'json').splitlines():
                    container = json.loads(row)
                    if container['State'] == 'exited':
                        service = container['Service']
                        print(compose('logs', '--no-color', '--tail', '35', service), flush=True)
                raise
            deadline = time.monotonic() + 40
            while True:
                status, _ = call(public + '/player/auth/login', 'POST', {})
                if status not in (502, 408):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Player did not become ready through Gateway')
                time.sleep(0.5)
            check('Gateway health', call(public + '/up')[0], 200)
            check('protected REST refuses forged headers without token',
                  call(public + '/player/players/' + str(uuid.uuid4()), headers={'X-Player-Id': str(uuid.uuid4())})[0], 401)
            check('public listener refuses internal session creation',
                  call(public + '/session/sessions', 'POST', {})[0], 403)
            for port, path in ((ports[1], '/sessions/' + str(uuid.uuid4())), (ports[2], '/sessions/' + str(uuid.uuid4()) + '/channels')):
                check(f'WS-only port {"Session" if port == ports[1] else "DM"} rejects ordinary REST',
                      call(f'http://127.0.0.1:{port}' + path, headers={'X-Session-Role': 'moderator'})[0], 404)

            accounts = []
            for role in ('moderator', 'junior'):
                name = role + '_' + uuid.uuid4().hex[:10]
                status, account = call(public + '/player/auth/register', 'POST', {
                    'username': name, 'email': name + '@utm.md', 'password': secrets.token_hex(16),
                })
                if not check('register ' + role + ' through Gateway', status, 201):
                    raise RuntimeError('Registration failed; cannot continue session checks')
                accounts.append(account)
            moderator, junior = accounts
            player_auth = {'Authorization': 'Bearer ' + moderator['token']}
            status, team = call(public + '/player/teams', 'POST', {'name': 'Compose check', 'ownerId': moderator['playerId']}, player_auth)
            check('create a real team through Gateway', status, 201)
            team_id = team['teamId']
            check('add junior member to the real team', call(public + f'/player/teams/{team_id}/members', 'POST',
                  {'playerId': junior['playerId']}, player_auth)[0], 201)
            status, session = call(public + f'/player/teams/{team_id}/sessions', 'POST', headers=player_auth)
            check('Player opens Session through Gateway port 8001', status, 201)
            session_id = session['sessionId']
            session_auth = {'Authorization': 'Bearer ' + session['sessionToken']}
            junior_auth = {'Authorization': 'Bearer ' + junior['token']}
            status, joined = call(public + f'/session/sessions/{session_id}/join', 'POST', headers=junior_auth)
            check('junior joins Session through Gateway', status, 200)
            junior_session_auth = {'Authorization': 'Bearer ' + joined['sessionToken']}
            check('Session read works with its issued token',
                  call(public + f'/session/sessions/{session_id}', headers=session_auth)[0], 200)
            negotiated_urls = {}
            for surface, expected_url in (
                ('session', f'ws://127.0.0.1:{ports[1]}/sessions/{session_id}/live'),
                ('dm', f'ws://127.0.0.1:{ports[2]}/ws?sessionId={session_id}'),
            ):
                status, negotiated = call(public + '/ws/negotiate', 'POST',
                    {'surface': surface, 'sessionId': session_id}, session_auth)
                if not check('Gateway negotiates ' + surface + ' WS', status, 200):
                    raise RuntimeError('Gateway WS negotiation failed')
                check('Gateway returns the published ' + surface + ' WS URL', negotiated.get('url'), expected_url)
                negotiated_urls[surface] = urlsplit(negotiated['url'])
            session_ws = negotiated_urls['session']
            dm_ws = negotiated_urls['dm']
            check('Session WS validates a real session token',
                  websocket_status(session_ws.port, session_ws.path + '?token=' + session['sessionToken']), 101)
            check('Session WS rejects an invalid token',
                  websocket_status(ports[1], f'/sessions/{session_id}/live?token=invalid'), 401)
            check('DM WS validates the same session token',
                  websocket_status(dm_ws.port, dm_ws.path + '?' + dm_ws.query + '&token=' + session['sessionToken']), 101)
            check('DM WS rejects an invalid token', websocket_status(ports[2], f'/ws?sessionId={session_id}&token=invalid'), 401)

            status, applicant = internal('/applicant/applicants', 'POST', {'sessionId': session_id})
            check('internal Gateway creates a real Applicant', status, 201)
            applicant_id = applicant['applicantId']
            check('moderator reads the real Applicant through Gateway',
                  call(public + f'/applicant/applicants/{applicant_id}/public', headers=session_auth)[0], 200)
            check('junior reads the real Applicant through Gateway',
                  call(public + f'/applicant/applicants/{applicant_id}/public', headers=junior_session_auth)[0], 200)
            check('public Gateway refuses the full internal Applicant view',
                  call(public + f'/applicant/applicants/{applicant_id}', headers=session_auth)[0], 403)
            check('ApplicantInitialized reaches Credential automatically',
                  internal(f'/credential/applicants/{applicant_id}/credentials/validate', 'POST')[0], 200)

            # Deliberate fixture setup for REST sharing, separate from the event
            # delivery check above. This must not turn missing propagation green.
            fixture_id = str(uuid.uuid4())
            event = {'type': 'ApplicantInitialized', 'payload': {'applicantId': fixture_id, 'sessionId': session_id,
                'documents': [{'type': 'student_id', 'status': 'valid', 'fields': {
                    'studentId': 'FAF230042', 'fullName': 'Ana Rusu', 'faculty': 'FCIM', 'major': 'FAF',
                    'year': 3, 'issuedAt': '2023-09-01', 'expiresAt': '2099-06-30',
                }}]}}
            compose('exec', '-T', 'credential', 'php', 'artisan', 'events:handle', input=json.dumps(event))
            status, documents = call(public + f'/credential/applicants/{fixture_id}/credentials', headers=session_auth)
            check('moderator reads Credential fixture through Gateway', status, 200)
            check('junior is refused by Credential',
                  call(public + f'/credential/applicants/{fixture_id}/credentials', headers=junior_session_auth)[0], 403)
            check('Session assigns channel access', call(public + f'/session/sessions/{session_id}/roles', 'POST',
                  {'assignments': [{'playerId': junior['playerId'], 'role': 'junior_mod',
                    'recordAccess': [], 'channelAccess': ['general-mod-chat']}]}, session_auth)[0], 200)
            check('Session starts the shift', call(public + f'/session/sessions/{session_id}/start', 'POST', headers=session_auth)[0], 200)
            status, _ = call(public + f'/dm/sessions/{session_id}/channels', 'POST', {'names': ['compose-check']}, session_auth)
            check('DM creates real channels through Gateway', status, 201)
            # The four default channels already exist; POSTing their names is
            # correctly a 409. List them and use the assigned general channel.
            status, channels = call(public + f'/dm/sessions/{session_id}/channels', headers=session_auth)
            check('DM lists channels using real Session access-check', status, 200)
            channel_id = next(channel['channelId'] for channel in channels if channel['name'] == 'general-mod-chat')
            check('DM posts using real Session access-check through Gateway',
                  call(public + f'/dm/channels/{channel_id}/messages', 'POST', {'content': 'Compose integration check'}, session_auth)[0], 201)
            check('DM shares Credential using forwarded identity through Gateway',
                  call(public + f'/dm/channels/{channel_id}/messages', 'POST', {'share': {
                      'source': 'credential', 'applicantId': fixture_id, 'credentialId': documents[0]['credentialId'],
                  }}, session_auth)[0], 201)
            check('Moderation internal decision listing works through Gateway',
                  internal(f'/moderation/sessions/{session_id}/decisions')[0], 200)
            check('Server Rules accepts internal creation without Authorization',
                  internal('/rules/rules', 'POST', {'sessionId': session_id, 'level': 1})[0], 201)
            check('University Record accepts Gateway identity',
                  call(public + '/records/records/academic-year', headers=session_auth)[0], 200)
            status, next_applicant = call(public + f'/session/sessions/{session_id}/next-applicant', 'POST', headers=session_auth)
            check('Session requests the next Applicant', status, 202)
            if status == 202:
                check('Session next-applicant exists in real Applicant service',
                      internal('/applicant/applicants/' + next_applicant['applicantId'])[0], 200)
        finally:
            subprocess.run([*command, 'down', '-v', '--remove-orphans'], capture_output=True, text=True, timeout=120)

    passed = sum(check['passed'] for check in checks)
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'passed': passed, 'total': len(checks), 'images': {
        'gateway': args.gateway_image, 'session': args.session_image,
        'applicant': args.applicant_image, 'credential': args.credential_image,
        'rules': args.rules_image, 'records': args.records_image,
        'player': config['services']['player']['image'],
        'dm': config['services']['dm-service']['image'],
        'moderation': config['services']['moderation-service']['image'],
        'ws_edge': config['services']['ws-edge']['image'],
    }, 'checks': checks}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{passed}/{len(checks)} checks passed. Disposable project removed.')
    return 0 if passed == len(checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
