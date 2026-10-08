# Gateway WebSocket contract and integration readiness

This document distinguishes the merged Gateway negotiation endpoint from pending
shared deployment work. It does not claim that the current Compose stack meets
Lab 2 routing requirements.

## Negotiation (merged Gateway PR #6)

POST /ws/negotiate on the public Gateway (port 8000), with
Authorization: Bearer <session-token> and JSON:

```json
{"surface":"session","sessionId":"<UUID>"}
```

The surface is session or dm. The Gateway uses Part 2 TokenReader.read(), rejects
player-only tokens, and requires the token session to match the requested UUID.
A successful response has surface, sessionId and url; no token is returned.
The client connects directly to that URL, not through the Gateway. No downstream
availability probe is made. Existing task timeout/concurrency middleware applies.

| Status | Error | Meaning |
|---|---|---|
| 401 | INVALID_TOKEN | Missing, invalid or non-session token |
| 422 | VALIDATION_FAILED | Invalid JSON, fields, surface or session UUID |
| 403 | SESSION_MISMATCH | Requested session differs from token session |
| 503 | WS_UNAVAILABLE | Missing or invalid public WS base URL |

SESSION_PUBLIC_WS_BASE_URL and DM_PUBLIC_WS_BASE_URL are client-visible ws/wss
base URLs, separate from Docker-internal REST upstream URLs. localhost values
are only suitable when the client runs on the Docker host.

## Session owner confirmation and pending deployment

Confirmed handshake path: /sessions/{sessionId}/live. Token transport is either
?token=<jwt> or Authorization: Bearer <jwt>. Session verifies the token itself
because this connection bypasses Gateway; this is the explicit WS authentication
exception. The owner reports pre-upgrade rejection for missing token (401),
session mismatch (403) and connection limit (429).

PLANNED, NOT VERIFIED IN THE SHARED DEPLOYMENT: separate WS listener on 3011,
plain HTTP returns 426 without reaching Express, REST remains private on 3001.
The owner reports the listener is implemented and tested locally, but not yet
merged/published. The planned image is
`catalinasiminiuc/pad-server-moderation-session-service:2.1.0`;
`2.0.1` does not contain the separate listener. Availability has not been verified.
After the owner confirms the merged change and published image, configure:

```dotenv
SESSION_PUBLIC_WS_BASE_URL=ws://localhost:3011
```

Publish only the dedicated WS listener. Do not change the current image's port
mapping before confirming it implements that listener.

## DM confirmed handshake; separate listener not implemented

Augustin confirms `/ws?sessionId=<UUID>&token=<session JWT>`. The token is
mandatory in the query string; do not assume Bearer headers are supported for DM.
DM validates it with Session's public key at the handshake. The owner reports
401 for an invalid token and 403 when the requested session differs from the token.

The Gateway's existing token-free `/ws?sessionId=<UUID>` response is compatible:
the client adds its own session token immediately before connecting. The Gateway
does not return, forward or append that token. For a browser client:

```javascript
// negotiated is the successful /ws/negotiate response; sessionToken is held locally.
const socketUrl = new URL(negotiated.url);
socketUrl.searchParams.set("token", sessionToken);
const socket = new WebSocket(socketUrl);
```

Do not log the resulting URL or store real tokens in exported Postman collections.
This example also works for Session's confirmed query-token transport.

BLOCKED FOR FINAL DEPLOYMENT: DM currently shares REST and WS on container port
3000 (host 3002 in the inspected Compose). A dedicated WS listener is not yet
implemented. Augustin must provide its port and published image tag after the
change. Separating the listener is DM owner's work, not a Gateway workaround.
Leave DM_PUBLIC_WS_BASE_URL unconfigured in the proposed final deployment until
those values are confirmed; negotiation then returns 503 WS_UNAVAILABLE for DM.
Do not publish the shared REST/WS listener as the final Lab 2 arrangement.

## Remaining owner deliverables

| Owner | Required before shared runtime verification |
|---|---|
| Session | Publish 2.1.0 and confirm the separate 3011 listener is in that image |
| DM | Implement a WS-only listener, confirm plain-HTTP rejection behaviour, port and published image tag |
| Gateway/shared stack | Confirm released Gateway image includes PR #6; wire Compose and migrate callers together |

No negotiation endpoint code change is required by the confirmed handshake paths.
No final shared Compose port/image changes have been applied by this documentation.

## Shared deployment and Postman migration checklist

Inspection baseline: shared dev 9c41b8a. It has no Gateway Compose service,
publishes REST ports, and includes Laravel mock authentication and legacy service
secrets. These require coordinated service/image updates, not just URL edits.

1. Confirm published image versions supporting Gateway identity headers and
   the two separate WS listeners. Confirm Gateway image includes negotiation.
2. Add Gateway with public 8000 and private internal 8001; mount only Player and
   Session public keys. Set REST upstream URLs using Compose names/internal ports.
3. Route client REST through http://localhost:8000/<service>/<path>. Route service
   REST through http://gateway:8001/<service>/<path>. Remove published REST ports
   together with those caller updates; never publish Gateway's internal listener.
4. Migrate Postman login/session setup to real tokens. Do not send mock tokens
   or manually forged identity headers as positive public authentication cases.
   Keep service-only setup requests separate: public access must return 403,
   and legitimate service setup must execute inside the Docker network.
5. Configure confirmed client-visible WS bases. Verify both negotiation and a
   real direct handshake, including missing-token/session-mismatch cases.
6. Check plain HTTP on Session WS returns 426; check the DM owner-confirmed
   HTTP rejection behaviour on its dedicated listener. Check REST service ports
   are unreachable from the host. Verify timeout/concurrency errors separately.

Gateway-only Docker checks passed on the user's machine: verify_negotiation.py,
verify_auth.py, verify_limits.py. Full-stack checks above remain pending.

The proposed topology source is gateway-lab2.mmd. It describes the target design,
not the currently running Compose stack; the existing architecture PNG is unchanged.

## Prepared development artifacts (not the final shared deployment)

`compose.gateway-dev.yaml` adds only Gateway, building your local PR #6 checkout.
It uses the actual shared Compose service names and internal ports. It does not
remove legacy REST publications or upgrade any service image. No private key is
mounted into Gateway. Set GATEWAY_SOURCE_DIR in your ignored .env and provide the
existing Player/Session public key files before using:

```powershell
docker compose -f docker-compose.yml -f compose.gateway-dev.yaml config --quiet
docker compose -f docker-compose.yml -f compose.gateway-dev.yaml up -d --build gateway
```

Import `postman/gateway-lab2.postman_collection.json`. Run its folders separately:
folder 1 needs no token; folder 2 requires configured WS bases and a real session
token; folder 3 instead expects both WS bases to be unconfigured. Supply the
matching sessionId and a different otherSessionId. Do not run folders 2 and 3 as
one suite. These checks do not establish real WebSocket connections.

Augustin confirms DM image 2.1.0 implements the query-token handshake described
above, but a separate WS listener is still absent. This is not a reason to publish
its shared REST listener in the final deployment.

Additional compatibility finding: the inspected local Server Rules middleware
MockAuthentication.php and University Record AuthenticateCaller.php consume
Bearer tokens. Gateway strips Authorization, so those local implementations
cannot serve authenticated forwarded calls unchanged. Confirm compatible service
releases before migrating their existing Postman success cases. The existing
collections have therefore been preserved as legacy checks, not relabelled as
passing Lab 2 checks.

Target architecture PNG: `docs/images/gateway-lab2-target.png`. Editable sources:
`docs/gateway-lab2.mmd` and `scripts/render_gateway_diagram.py` (Pillow renderer).
The existing Lab 1 diagram remains intact.
