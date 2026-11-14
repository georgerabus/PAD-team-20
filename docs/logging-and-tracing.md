# Logging and tracing

How every service in the system writes logs, how a request is followed across
services, and where both end up. Every service follows this; the sections at
the end say exactly what changes in each one.

## The picture

```
 every service ──LogBatch events on topic `logs`──► Message Broker ──► Loki  source="broker" ──► Gateway GET /logs
       │                                                               │
       ├──stdout (the same JSON lines)──► Promtail ──────────────────► Loki  source="stdout" ─┐
       │                                                                                     ├─► Grafana
       └──spans (OTLP/HTTP, port 4318)──► Tempo ────────────────────────────────────────────┘
                                            └── service graph ──► Prometheus
```

- **Logs travel through the broker.** Every service sends its lines, in
  batches, as events on the `logs` topic; the broker writes them into Loki,
  labelled `source="broker"`. That is the system's log, and the one the
  Gateway's `GET /logs` downloads. The lines of an instance that crashed, was
  removed by the breaker, or was scaled away are still there afterwards.
- **Promtail is the backup.** Every service also writes the same lines to
  standard output, and Promtail ships those to Loki as `source="stdout"`. It
  keeps what cannot go through the broker: the lines about the broker being
  down, what a process prints as it crashes, and every service that has no
  sender yet. Grafana reads them; the download does not, so nothing is
  counted twice.
- The in-memory ring behind each service's own `GET /logs` stays, as a way to
  look at one live instance, and as the download's fallback when Loki is down.
- **Every user request carries one trace id from the Gateway to the last
  service it reaches**, across HTTP, the broker's envelope, gRPC and queued
  events. Every log line written while handling it carries that id.
- **Spans go to Tempo.** Grafana shows a request as a waterfall (Gateway →
  broker → Session → broker → Moderation, with the time spent in each), and
  links each span to the log lines written inside it, and each log line back
  to its trace.
- **Errors carry their stack** in the line itself, as a field, not as loose
  text that a reader has to stitch back together.

## The log line

One JSON object per line on standard output. No prefix, no colour codes.

```json
{"ts":"2026-11-13T13:43:23.568Z","level":"error","service":"session","instance":"eb7163439535","context":"AppExceptionFilter","message":"Unhandled failure on POST /sessions/42/start","traceId":"4bf92f3577b34da6a3ce929d0e0e4736","spanId":"00f067aa0ba902b7","error":{"type":"TypeError","message":"Cannot read properties of undefined (reading 'id')","stack":"TypeError: Cannot read properties of undefined (reading 'id')\n    at SessionsService.start (/app/dist/sessions/sessions.service.js:88:31)\n    ..."}}
```

| Field | Always | What it holds |
|---|---|---|
| `ts` | yes | ISO-8601, UTC, milliseconds, `Z` |
| `level` | yes | `verbose`, `debug`, `log`, `warn`, `error` or `fatal` |
| `service` | yes | The name the service registers under in Service Discovery: `player`, `session`, `broker`, `gateway`, … |
| `instance` | yes | The container's hostname (the short container id) |
| `context` | yes | Which part of the service wrote it: `Request`, `Delivery`, `AppExceptionFilter`, … |
| `message` | yes | One line of text for a person |
| `traceId` | when inside a trace | 32 lowercase hex characters |
| `spanId` | when inside a trace | 16 lowercase hex characters |
| `error` | when an exception is logged | `{"type", "message", "stack"}`; `stack` is the full multi-line trace |

The first six fields are the ones `GET /logs` already returns, so nothing that
reads them breaks. A service may add fields of its own after these (the
Gateway's request lines keep `method`, `path`, `status`, `durationMs`); a
reader ignores what it does not know. Lines written outside any request (startup, registration,
health checks) have no `traceId`; that is expected.

**Levels.** A request line is `log` for 2xx/3xx, `warn` for 4xx, `error` for
5xx. Requests for `/status`, `/up`, `/logs` and `/metrics` are `debug`: they
are polled every few seconds by Service Discovery and Prometheus, and were most
of the collected log before this.

## Following a request: the trace context

The standard W3C Trace Context header, so the OpenTelemetry SDK of every
language reads and writes it without extra code:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
                 └────────── trace id ─────────┘ └─ parent span ┘
```

| Hop | Carried as |
|---|---|
| Client → Gateway | Started by the Gateway. A valid incoming `traceparent` is continued, so a Postman request can set its own |
| Gateway → client | `X-Trace-Id: <trace id>` on every response, errors included, except `/up`, `/status`, `/logs` and `/metrics`, which are not traced. Copy it into the Gateway's `GET /logs?traceId=` or into Grafana |
| Anyone → broker, HTTP (`POST /messages`) | `traceparent` request header |
| Broker → service, HTTP (`/broker/deliver`) | `traceparent` request header, with the broker's delivery span as parent |
| Anyone → broker → service, gRPC | `traceparent` metadata key; the broker forwards it with its own span as parent |
| Queued event (topic) | Stored with the event in `queues.db` and sent on every delivery attempt, so an event delivered after a broker restart still joins its trace. A dead letter keeps it too: `GET /dead-letters` shows its `traceId` |
| Service → `gateway:8001` (REST not yet migrated) | `traceparent` request header |

Read the trace id by position, never by matching the whole header: the last
field is flags, and the OpenTelemetry SDKs send `03` as well as `01`.

**The trace is not in the envelope.** It travels in the `traceparent` HTTP
header of `POST /messages` and in the `traceparent` gRPC metadata key, which
the OpenTelemetry SDKs read and write themselves. The envelope is unchanged,
so a service that has not adopted tracing sends exactly what it sent before
and is never refused for it. On a queued event the broker keeps
`traceparent` in its own column beside the envelope, not inside it. A
`LogBatch` carries no `traceparent` at all: sending logs is neither traced
nor logged.

`correlationId` in the envelope is unchanged. The trace id is what joins logs
and spans across services.

## Spans

OpenTelemetry SDK in each service, exporting OTLP over HTTP to
`OTEL_EXPORTER_OTLP_ENDPOINT` (`http://tempo:4318` in Compose).

- `service.name` is the registered name (`player`, `broker`, …);
  `service.instance.id` is the hostname, the same value as `instance` in the
  log line.
- One server span per request received, one client span per call made.
- **Not traced:** `/status`, `/up`, `/logs`, `/metrics` — the polls would bury
  the requests.
- With `OTEL_EXPORTER_OTLP_ENDPOINT` unset, trace ids are still created,
  propagated and logged; only the export is off. Nothing fails because Tempo
  is not running.

## Where to look

| Question | Where |
|---|---|
| Everything one request did, as a timeline | Grafana → Explore → Tempo, search by trace id, or click the trace id on any log line |
| The log lines of one request, across services | Grafana → *PAD Team 20 — Logs* dashboard, `traceId` box; or the Gateway's `GET /logs?traceId=<id>` |
| All errors, with stacks | *PAD Team 20 — Logs* dashboard, *Errors* panel |
| Which service calls which, how often and how slowly | Grafana → Explore → Tempo → Service Graph |
| A file to download (grade 4) | `GET /logs?since=&service=&level=&traceId=&limit=` on the **Gateway**, with `X-Logs-Token` |

## The download: `GET /logs` on the Gateway

The Gateway is the system's way in for a person, so the system's log is
downloaded there, on its public port: newline-delimited JSON, oldest first,
as `pad-team-20.log`.

| Parameter | Meaning |
|---|---|
| `since` | ISO-8601, inclusive, compared as a moment (an offset is honoured; none means UTC) |
| `service` | One service, by its registered name: `session`, `rules`, `dm`, … |
| `level` | A floor: `warn` is warn, error and fatal |
| `traceId` | Every line of one request, from every service it reached: the `X-Trace-Id` the Gateway returned |
| `limit` | The newest N, after the other filters. 5000 by default, at most 100 000 |
| `source` | `broker` by default: the lines sent through the broker, the system's log. `stdout` reads Promtail's copy instead, which has the services that do not send yet; `all` is both, each line once |

- **Who may read it:** an operator, with `X-Logs-Token` equal to `LOGS_TOKEN`
  in `.env`. A player's token does not open it: the lines say which applicant
  is an impostor. With `LOGS_TOKEN` unset it answers `503`.
- **Where it reads from:** Loki, so it includes instances that crashed, were
  removed or were scaled away. If Loki does not answer, it asks Service
  Discovery where the instances are and asks each for its own `GET /logs`.
  `X-Logs-Source` says which (`loki` or `instances`); with `instances`,
  `X-Logs-Unreachable` counts the ones that did not answer.
- **Lines not yet in the shared shape** (services still writing Nest text,
  Laravel lines or nginx access lines) are read into it as well as they can
  be: level, context and message are recovered from the text, `service` and
  `instance` from the container.
- On the **internal** port 8001, `GET /logs` is the Gateway's own recent lines,
  like every other service's `GET /logs`.

Service Discovery takes no part in this beyond saying where instances are.
Its own `GET /logs/all` is gone.

## Sending lines: the `logs` topic

### The message

An ordinary event in the broker's envelope, sent to `POST {BROKER_URL}/messages`:

```json
{"messageId": "<uuid>", "kind": "event", "source": "<your service>", "target": null,
 "topic": "logs", "operation": "LogBatch", "identity": null,
 "payload": {"lines": [ <log lines, as above> ]}}
```

- At most **100 lines** per batch, and the body under the broker's
  `MAX_BODY_BYTES` (1 MiB). The broker answers `202 {"accepted": n}`; more than
  100 lines, or another operation on `logs`, is `422`.
- No `traceparent` header, and no other envelope field: the broker refuses
  fields it does not know.

### What a sender does

- Hands every line it writes to a buffer, and sends a batch **once a second,
  or as soon as 100 lines are waiting**.
- **A request never waits on it.** Adding a line is an append; sending
  happens on its own thread or timer.
- **Bounded:** past its capacity (1000 lines by default) the oldest line is
  dropped and counted. While the broker is down, the newest lines are the ones
  worth keeping, and standard output has them all anyway.
- **Not traced, not logged:** no span, no request line for the send — a line
  about sending lines would be sent in the next batch, forever. A failure is
  reported at most once a minute, on standard output only.
- A batch that failed is sent again first on the next tick; nothing else is
  retried.
- `LOG_SHIPPING=off` switches it off. Where the broker is: `BROKER_URL` in the
  Python services, `BROKER_BASE_URL` in the NestJS ones (the name Session
  already used); both default to `http://broker:8000`.

Ready-made: `log_shipper.py` in the Gateway and Service Discovery (Python,
standard library only) and `src/logs/broker-log-sender.ts` in Player and
Session (NestJS). Copy the one for your language.

### What the broker does with them

- `logs` takes its own path inside the broker: no SQLite store, no retries,
  no dead letters. A Loki outage must not fill `dead_letters` and push out the
  business messages it exists for.
- The lines wait in a **bounded in-memory queue** that drops the oldest when
  full and counts the drops, and are pushed to Loki about once a second.
- **Nothing about `logs` is logged or traced** — no request line, no `ROUTE`,
  `QUEUED`, `DELIVERED` or `ACKED`.
- It registers in Service Discovery with `topics: ["logs"]`, so `logs` shows in
  `GET /topics`, but a batch is handled in-process: it is never delivered to a
  `/broker/deliver`, the broker's own included. Its own lines enter the same
  queue directly.
- Loki labels are `service`, `level` and `source="broker"` only. `traceId` goes
  in the line and as structured metadata, never as a label: a label per
  request would be an index entry per request.

## What changes in each service

### Already done in this change

| Service | Owner | |
|---|---|---|
| Gateway | Loredana | Starts the trace, `X-Trace-Id` on every response, `traceparent` to the broker and to the services it still calls directly, JSON lines without the `INFO:` prefix, the system's log download `GET /logs`, and a sender (`log_shipper.py`) |
| Message Broker | George | Continues the trace on `POST /messages` and gRPC, forwards `traceparent`, keeps it with queued events and dead letters, one span per delivery attempt; the `logs` topic into Loki, as above |
| Player, Session | Cătălina | OpenTelemetry for HTTP, Express, gRPC and Postgres; JSON log lines; stack kept on errors; a sender (`broker-log-sender.ts`) |
| Service Discovery | George / Cătălina | JSON lines with `service` and the caller's trace; routing lookups at `debug`; a sender (`log_shipper.py`); `/logs/all` removed |

### Discord DMs and Moderation (NestJS) — Augustin

Copy three files from Player and register them the same way:

1. `src/tracing.ts`, imported as the **first line** of `src/main.ts`, before
   Nest is imported, so the instrumentations can patch `http`, `express`,
   `@grpc/grpc-js` and `pg` before anything loads them. Set `service.name` to
   `dm` / `moderation`.
2. `src/logs/json.logger.ts` in place of the current logger. It writes the
   line above and keeps the stack that Nest passes as the second argument of
   `error()`. Your existing log buffer is passed to it as its `sink`.
3. `src/logs/broker-log-sender.ts`, added as a second sink, which sends the
   lines to the `logs` topic.

Plus the OpenTelemetry packages from Player's `package.json`, at the same
pinned versions, and Node 22.15 or later (`instrumentation-express` needs it;
the images run 22.23).

Outgoing calls through the broker and to `gateway:8001` need no change: the
HTTP and gRPC instrumentations add `traceparent` themselves. Check with one
call that the trace in Grafana has your service in it.

### Applicant, Credential, Server Rules, University Record (PHP) — George, Loredana

The minimum, which keeps every request of yours inside its trace and in the
log search:

1. **Read** `traceparent` from the incoming request (HTTP header, or gRPC
   metadata in RoadRunner) in the middleware that already writes the request
   line. Take the trace id (characters 4–35) and the span id (37–52).
2. **Write** them as `traceId` and `spanId` on every line logged while handling
   that request, and add `service`. Log exceptions with an `error` object whose
   `stack` is `$e->getTraceAsString()`.
3. **Pass it on**: set the same `traceparent` on every outgoing call — the
   gRPC metadata of `Broker.php`, the `POST /messages` header, any call to
   `gateway:8001`.

4. **Send the lines to the broker without making a request wait.** Under
   Apache `mod_php` there is no long-lived process to hold a buffer or a
   one-second timer, so:
   - each request appends its lines, as NDJSON in the shape above, to a local
     file (`storage/logs/ship.ndjson`), and to standard output as before;
   - a small long-running process next to Apache and RoadRunner,
     `php artisan logs:ship`, reads the file from where it left off and sends
     `LogBatch` events as described in *What a sender does*: at most 100
     lines, once a second, no `traceparent`, nothing logged about the send. It
     remembers its offset, so a restart does not send lines twice, and
     truncates the file once everything in it was accepted.

   A request never waits on the broker this way. George does this for
   Applicant and Credential; the same command fits Server Rules and
   University Record.

Your services then show in the log search and keep the chain unbroken, but
have no span of their own in the waterfall: the caller's span covers the time.
For spans as well, add `open-telemetry/sdk`,
`open-telemetry/exporter-otlp` and `open-telemetry/opentelemetry-auto-laravel`
with Composer and the `opentelemetry` PHP extension in the Dockerfile; the
environment variables are the same as everyone else's.

### Checking your service

```sh
# One request through the Gateway; the response says which trace it started.
curl -si http://localhost:8080/<your-route> -H "Authorization: Bearer $TOKEN" | grep -i x-trace-id

# Every line of that request, from every service it reached.
curl -s "http://localhost:8080/logs?traceId=<id>" -H "X-Logs-Token: $LOGS_TOKEN"
```

Your service is done when its lines show up in the second command with the
same `traceId`, and its errors carry an `error.stack`. The second command reads
what came through the broker; if your lines are only in
`...&source=stdout`, the tracing works but the sender does not yet.
