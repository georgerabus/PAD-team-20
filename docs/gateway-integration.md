# Common Gateway integration

Verified on 8 October 2026. This is the integration work on
`feat/gateway-service-integration`, based on CPR `dev` at `9c41b8a`. That work is now merged into the common repository; the results below remain
a historical run, not a new verification of Session 2.1.0. Container startup and functioning
authentication do not establish that the full Lab 2 game is ready.

## Scope and ownership

This file and the JSON check report are supporting notes added for verification;
the Lab 2 PDF does not prescribe these filenames or this test suite.
It explicitly requires a Gateway README and an updated architecture diagram.
The common repository also requires a verification summary and board reference
in each PR. Test counts are diagnostics, not laboratory grades.

George took common Compose integration: add Gateway, configure connections,
select the owners' published image tags and test the deployment. Each teammate
still implements their own service changes and their agreed Gateway part:

| Owner | Individual services |
|---|---|
| George | Applicant and Credential |
| Cătălina | Player and Session |
| Loredana | Server Rules and University Record |
| Augustin | Discord DMs and Moderation |

The deployment entry and image configuration belong to George's Gateway Part
1. Authorization is Part 2 and limits/CI Part 3; their merged implementations
are reused. Part 4 owns WS negotiation and the final whole-system integration
check. Providing deployment configuration or diagnostic results does not
transfer that final integration work to George. The WS negotiation implementation
is already merged in Gateway PR #6, authored by Loredana.

Failures below identify separate service work or dependencies; they do not
transfer that implementation to the Compose author. Event delivery is a game
integration concern outside the HTTP-only Gateway routing check. The PDF does
not explicitly require RabbitMQ; shared transport choices need team agreement.

## What this change delivers

The common Compose starts Gateway, all eight domain services, eight separate
PostgreSQL databases and a WS-only Caddy edge. Client REST enters Gateway at
`http://127.0.0.1:8080`; its internal listener, port 8001, stays private. No
domain REST or database port is published.

Database health checks use TCP on 127.0.0.1. PostgreSQL's initialization server
accepts only local socket connections; checking that socket marked a fresh DB
healthy too early and caused University Record's startup migration to fail
with Connection refused. Waiting for TCP prevents that premature startup.

Player calls Session through `http://gateway:8001/session`. DM's Session,
Credential and University Record URLs, and Moderation's Applicant, Credential,
Rules and Session URLs, also point through port 8001. Gateway's DM and
Moderation upstreams use `dm-service:3000` and `moderation-service:3000`.

Gateway receives only the public Player/Session signing keys. The private keys
remain with their issuers. Applicant and Credential no longer receive a Session
key or SERVICE_SECRET. Credential retains CREDENTIAL_ISSUER_SECRET for signing
documents.

Session serves its WebSocket on a listener of its own since 2.1.0, published
as 3011: it handles upgrades and answers `426` to ordinary HTTP, which never
reaches a route. DM still shares one port with its REST routes, so Caddy
publishes only its `/ws` upgrades on 3002 and returns 404 for the rest.
Session and DM still validate their own WS handshakes. Gateway PR #6
implements authenticated `POST /ws/negotiate`. SESSION_PUBLIC_WS_BASE_URL and
DM_PUBLIC_WS_BASE_URL tell it the externally reachable addresses; Compose
points the first at Session itself and the second at the WS-only edge.

The three accessible submodules are pinned by this working tree to:

| Service | Merged `dev` commit |
|---|---|
| Applicant | `3bc66c8c2d1f003389b9f022728209ddf5eac123` |
| Credential | `d8c4f55950842ef8f1a6f6f6d2ead8a0a08902a2` |
| Gateway | `a9e5a565d98dd892aba409778e3b99dc67b6d937` |

The six other private source repositories could not be fetched with the
available access. Their existing CPR pins are retained. Published images were
inspected and exercised independently of access to those sources.

## Images and remaining dependencies

| Service | Published image checked | Result / requirement |
|---|---|---|
| Player | `catalinasiminiuc/pad-player-service:2.0.0` | Real Player → Gateway → Session flow passed |
| Session | `catalinasiminiuc/pad-server-moderation-session-service:2.2.0` | Identity, WS and the real outgoing clients through port 8001 all passed |
| Discord DMs | `augustinploteanu/pad-dm-service:2.1.0` | Real Session access-check and Credential sharing passed |
| Moderation | `augustinploteanu/pad-moderation-service:2.1.0` | Internal decision listing passed; full decision flow remains unverified |
| Applicant | `georgerabus/pad-applicant-service:2.0.0-rc.1` | Published from the merged commit above; real create/read passed |
| Credential | `georgerabus/pad-credential-service:2.0.0-rc.1` | Published from the merged commit above; identity, roles and sharing passed |
| Server Rules | `loredanaaaa/server-rules-service:1.0.1` | Legacy bearer-token mock; incompatible with Gateway stripping Authorization |
| University Record | `loredanaaaa/university-record-service:1.0.1` | Legacy bearer-token mock; incompatible with Gateway stripping Authorization |
| Gateway | Local `pad-gateway-service:dev`, built from `a9e5a56` | Confirm a published repository and tag before team deployment |

The two `2.0.0-rc.1` images are published for both linux/amd64 and linux/arm64.
Their manifest digests are:

- Applicant: `sha256:6255b7e8a2eafaedba0fb6a3044cf1911e3586c0c03beb3ae422723aa0a9e3c2`
- Credential: `sha256:ca0dfa4cb6caa117750b05d8f4eb133b3a2a5802bcc760b49146489507671dcf`

These candidate publications contain the authentication migration. They do not
complete Applicant/Credential task limits, CI or real event delivery. Manual
candidate publication does not prove the Lab 2 CI requirement.

Gateway's merged workflow publishes on `master` and manual dispatch under
`DOCKERHUB_USERNAME/pad-gateway-service`. Augustin said it uses his Docker Hub
account; the account name in secrets and the resulting image still need a
confirmed publication. The workflow's existence in `dev` is not evidence that
an image was pushed. Keep the `master` trigger required for the release.

`GATEWAY_IMAGE`, `SERVER_RULES_IMAGE` and `UNIVERSITY_RECORD_IMAGE` intentionally
have no default in `.env.example`. Fill them with confirmed, compatible
`repository:tag` references. The old Rules/Records tags are used only by the
diagnostic test below. Session also needs an owner's image with real outgoing
HTTP clients and its documented configuration; `2.0.1` has no real client
implementation that can be enabled just by adding URLs to Compose.

## Verification

The machine-readable report is
[`gateway-integration-checks.json`](gateway-integration-checks.json). The
integration run passed **37 of 41 checks** with the published Applicant and
Credential candidate images and the local Gateway image. Exit status 1 is the
expected result while the four integration failures remain:

| Check | Expected | Actual | Work needed |
|---|---|---|---|
| ApplicantInitialized automatically reaches Credential | 200 | 404 | Replace George's log-only EventPublisher / manual consumer with real delivery and test it |
| A shift scores above zero | >0 | 0 | Follows from the row above: `POST /moderation/decisions` answers `404 APPLICANT_NOT_FOUND` because Credential never learns the applicant, so Moderation's decision log stays empty and Session, which builds the result from that log, scores the shift zero |
| Rules internal creation through Gateway | 201 | 503 | Loredana: publish Rules with Gateway identity and internal-route authentication |
| University Record read through Gateway | 200 | 503 | Loredana: publish Records with Gateway identity and preserved access rules |
| Session's next applicant exists in real Applicant | 200 | 200 | Done in Session 2.2.0: the Applicant, Server Rules and Moderation mocks are real HTTP clients through `gateway:8001` |

The successful checks include fresh registrations and a real team/session,
public rejection of internal endpoints, rejection of forged identity without
a token, Applicant reads for both roles, Credential's junior-role rejection,
real DM access checks and sharing through internal Gateway, private port
configuration, negotiated Session/DM URLs and WS handshakes at those returned
addresses accepting real tokens and refusing invalid ones. Credential sharing
uses a separately labelled manual event fixture;
automatic propagation is tested independently and remains a failure.

Gateway's `tests/verify_negotiation.py` passed all 15 checks on the rebuilt
`a9e5a56` image. Gateway's `tests/verify_auth.py` and `tests/verify_limits.py` passed 19 and
17 checks respectively against the rebuilt `04f82a8` image. Those results
cover Gateway's limits, not the limits of all eight domain services.

To reproduce the current diagnostic run from the CPR directory:

```bash
python3 tests/verify_compose_gateway.py \
  --gateway-image pad-gateway-service:dev \
  --rules-image loredanaaaa/server-rules-service:1.0.1 \
  --records-image loredanaaaa/university-record-service:1.0.1 \
  --report docs/gateway-integration-checks.json
```

Build that local Gateway image from its merged `dev` if it is not available:

```bash
docker buildx build --builder default --load \
  -t pad-gateway-service:dev ./pad-gateway-service
```

After compatible images are published, rerun with their exact references using
`--gateway-image`, `--rules-image`, `--records-image` and `--session-image`.
The test generates temporary keys/passwords, picks loopback ports, starts a
separate Compose project and removes that project's containers and volumes.
It does not read or alter the project's `.env` or an existing deployment.
It checks selected integration paths, not every endpoint or realtime event.

## Team deployment and review

Use the setup in the root README once the required images are available. Each
DB password and CREDENTIAL_ISSUER_SECRET can be generated with
`openssl rand -hex 32`. The Laravel Rules/Records APP_KEY values require
`base64:` followed by `openssl rand -base64 32`. Keep `.env` and signing keys
out of Git. The REST port is configurable by GATEWAY_HTTP_PORT; the default
8080 avoids other local applications using 8000.

The original integration changes are now present in shared dev.
Open a board issue for this integration and link it in a draft PR from
`feat/gateway-service-integration` to `dev`. Ask the owners of affected
services to review it. Supply and test the compatible images and complete the
configuration supplied by their owners. Each owner completes their real
clients/event handling in separate service tasks before the team presents
this as a functioning game.
After review and merge, colleagues fetch the common `dev` and pull its pinned
images. Merging a private service PR or publishing an image does not update
their common Compose automatically.

Other Lab 2 work still needs its own evidence: all-service task limits,
all-service CI publication, full realtime delivery, and a
Postman/demo flow updated for Gateway. CPR `dev` goes into `master` only when
the lab is ready to present, as required by the repository workflow.


### Session 2.1.0 follow-up (9 October 2026)

The image is published for both architectures and already selected by Compose.
The historical 37/41 report above is not evidence for the new listener. Rerun
`tests/verify_compose_gateway.py`; its Session checks now include Bearer transport,
missing token and mismatched session, alongside query-token and plain-HTTP checks.
No new runtime pass count is claimed. DM's Caddy edge remains unchanged, pending
agreement on the difference from the planned service-owned dedicated listener.


### User-run follow-up: 43/45 checks passed (9 October 2026)

The user reran the updated diagnostic with local images
`loredanaaaa/server-rules-service:2.0.0-rc.1` and
`loredanaaaa/university-record-service:2.0.0-rc.1`, local
`pad-gateway-service:dev`, and published Session 2.1.0.
This is a user-supplied console result, not a regenerated JSON report.
The historical JSON and 37/41 run above have not been overwritten.

Rules internal creation now returns 201; Records reference read with Gateway
identity returns 200. Session query-token and Bearer handshakes return 101;
missing/invalid tokens return 401 and mismatched session returns 403.
Session plain HTTP returns 426; DM edge plain HTTP returns 404.

Two checks remain failing with 404:
- ApplicantInitialized automatically reaches Credential (George's event delivery).
- Session next-applicant exists in real Applicant (Session outgoing integration).

Both candidate Rules/Records images are local builds only. No multi-platform
publication is claimed. Their service suites passed locally: Rules 18 tests /
126 assertions; Records 26 tests / 181 assertions. Fixture-based tests do not
establish real University Record event ingestion. All-service limits, CI and
complete game/realtime flows still need their own implementation and evidence.

The runner now downloads missing images before starting the readiness timer,
shows Docker progress, and allows 300 seconds for Compose readiness (600-second
outer process limit). Cached images are reused; the local Gateway image must
already exist. The earlier 180-second startup timeout is not counted as a
service assertion failure.


### Candidate publication verified (9 October 2026)

Docker Hub now lists both Gateway-compatible candidates for linux/amd64 and
linux/arm64. `.env.example` selects these versions; existing private `.env` files
must be updated by their owners. This supersedes the earlier local-only status.

- `loredanaaaa/server-rules-service:2.0.0-rc.1`:
  `sha256:12f7b512a738625e0622874bd6e413814be8f2afe8cf61076130949f18958077`
- `loredanaaaa/university-record-service:2.0.0-rc.1`:
  `sha256:8dbbbf4db814e9696830d216aee13ecfb4a56b10dcfa2e88c19834ccd6e44ed8`

Manifest availability is verified, not ARM64 execution. The 43/45 result used
local candidates before publication; the published-image follow-up result is recorded below. Publication was
manual, not evidence of automatic CI publication on merge.


### Published-candidate runtime follow-up (user-run, 9 October 2026)

After the instructed pulls of both published 2.0.0-rc.1 candidates, the user
reported 43/45 checks passed again. Rules internal creation returned 201 and
Records Gateway identity read returned 200. The same two 404 failures remain:
automatic ApplicantInitialized delivery to Credential, and the real Applicant
lookup for Session's next-applicant result. Gateway was still the local dev image.
This is the user's Windows Docker linux/amd64 run; ARM64 runtime was not tested.
The console summary is recorded here without replacing the historical JSON report.


### CI-published request-limit candidates with Session 2.2.0 (user-run)

The user confirmed successful test and publish jobs on main for both services,
then pulled and tested server-rules-service:2.0.0-rc.2 and
university-record-service:2.0.0-rc.2 with Session 2.2.0. The shared integration
result was 44/45. Rules internal creation returned 201, Records identity read
returned 200, and Session next-applicant was present in Applicant (200).
Session and DM WebSocket checks passed. The only failing check in this suite
was automatic ApplicantInitialized delivery to Credential (404).

Gateway still used the local pad-gateway-service:dev image. This is not yet
validation of an entirely registry-pulled stack or proof of complete Lab 2
business logic. The suite does not establish all event flows. Runtime tests
were linux/amd64; ARM64 runtime has not been tested. Existing private .env
files must be updated separately; .env.example now selects both rc.2 images.


### Published Gateway confirmed

Docker Hub tag `augustinploteanu/pad-gateway-service:2.0.0` has manifest digest
`sha256:22b582856da6c07cb05cb78b44011df0f6b628529eddde31fefc66d1816b7247`,
matching the successful Gateway CI publication log supplied by the user.
The tag lists linux/amd64 and linux/arm64. `.env.example` now selects it.
The earlier 44/45 result used the local Gateway image; a full integration run
with this published Gateway is still pending. Private .env files are unchanged.


### Registry-only integration follow-up

The user subsequently pulled the published Gateway 2.0.0 and ran the shared
suite with Rules/Records 2.0.0-rc.2 and Session 2.2.0. Result: 44/45 passed.
This supersedes the pending published-Gateway runtime check above. The only
failed assertion was ApplicantInitialized reaching Credential automatically (404).

Source audit also identifies gaps NOT covered by this suite: University Record
still binds ApplicantEventSource to FixtureApplicantEventSource, and Server Rules
still binds RulesUpdatedPublisher to DatabaseMockRulesUpdatedPublisher. The
Records academic-year check does not prove real applicant-record materialization.
These adapters must be replaced for complete real event flows; the common README
specifies RabbitMQ, whose deployment and exchange/routing contract must align with
the Applicant/Credential and Moderation owners. Do not describe 44/45 as full Lab 2
completion or attribute all remaining work solely to Credential.
