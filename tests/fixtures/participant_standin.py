"""A stand-in saga participant for verify_saga.py, until University Record
serves its step.

It registers in Service Discovery under REGISTER_AS, answers its health checks
on GET /status, and answers what the broker delivers on POST /broker/deliver,
as the CPR README's "What a participant serves" asks: CreateApplicant 201
{applicantId}, DeleteApplicant 200 {applicantId, deleted}. POST /mode
{"refuse": "<operation>"} makes it refuse that operation with 422 instead.
GET /recorded answers every delivery it has received and the applicants it
keeps, both lost when it restarts.
"""

import json
import os
import socket
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DISCOVERY = os.environ['SERVICE_DISCOVERY_URL']
deliveries = []
kept = set()
mode = {'refuse': None}
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def answer(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/status':
            return self.answer(200, {'status': 'ok', 'load': {'inFlight': 0, 'limit': 100}})
        if self.path == '/recorded':
            with lock:
                return self.answer(200, {'deliveries': deliveries, 'kept': sorted(kept)})
        self.answer(404, {'error': 'NOT_FOUND', 'message': self.path, 'details': {}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'null')
        if self.path == '/mode':
            with lock:
                mode.update(body)
                return self.answer(200, mode)
        if self.path != '/broker/deliver':
            return self.answer(404, {'error': 'NOT_FOUND', 'message': self.path, 'details': {}})
        operation, applicant = body.get('operation'), (body.get('payload') or {}).get('applicantId')
        with lock:
            deliveries.append(body)
            if operation == mode['refuse']:
                status, payload = 422, {'error': 'STANDIN_REFUSED', 'message': 'The stand-in refuses.', 'details': {}}
            elif operation == 'CreateApplicant':
                status, payload = (200 if applicant in kept else 201), {'applicantId': applicant}
                kept.add(applicant)
            elif operation == 'DeleteApplicant':
                status, payload = 200, {'applicantId': applicant, 'deleted': applicant in kept}
                kept.discard(applicant)
            else:
                status, payload = 404, {'error': 'UNKNOWN_OPERATION', 'message': operation, 'details': {}}
        self.answer(200, {'status': status, 'payload': payload})


def register(name):
    body = json.dumps({'name': name, 'url': f'http://{socket.gethostname()}:8000'}).encode()
    while True:
        try:
            request = urllib.request.Request(DISCOVERY + '/register', data=body,
                headers={'Content-Type': 'application/json'}, method='POST')
            urllib.request.urlopen(request, timeout=5).close()
            return
        except OSError:
            time.sleep(1)


threading.Thread(target=register, args=(os.environ['REGISTER_AS'],), daemon=True).start()
ThreadingHTTPServer(('', 8000), Handler).serve_forever()
