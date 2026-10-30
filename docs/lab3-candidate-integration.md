# Lab 3 candidate integration

These are manually published integration candidates from the tested `dev`
commits, not the final Lab 3 release. The release PRs remain drafts:
[SD #7](https://github.com/georgerabus/pad-service-discovery/pull/7),
[Applicant #22](https://github.com/georgerabus/pad-applicant-service/pull/22) and
[Credential #22](https://github.com/georgerabus/pad-credential-service/pull/22).
Merge into `master` only once the lab is ready to present. Candidate
publication does not replace the required release CI run.

## Published candidates

| Service | Image | Source commit |
|---|---|---|
| Service Discovery | `georgerabus/pad-service-discovery:3.2.0-rc.1` | [`cd0d247`](https://github.com/georgerabus/pad-service-discovery/commit/cd0d24742e2519e750e9f17fdab4d6c343bb5175) |
| Applicant | `georgerabus/pad-applicant-service:3.0.0-rc.2` | [`c819347`](https://github.com/georgerabus/pad-applicant-service/commit/c8193473842d4a41cac7bbdad7c76fcd551fa243) |
| Credential | `georgerabus/pad-credential-service:3.0.0-rc.2` | [`bead102`](https://github.com/georgerabus/pad-credential-service/commit/bead1025043ec0de1204de7ce10f09b2b3f8eb42) |

All three manifests include `linux/amd64` and `linux/arm64`. Build contexts
were exported from those exact commits with `git archive`, excluding local
credentials, dependencies and runtime state. The downloaded amd64 images'
`org.opencontainers.image.revision` labels match the commits above.

Manifest index digests verified against the registry:

| Service | Digest |
|---|---|
| Service Discovery | `sha256:a08151461ea4a1f04ea662859a1d53d2badc3ed1a650d661a58526eba0a221c3` |
| Applicant | `sha256:697a9f1941d56da47a92f719e1c1d8761be3b9a239936547e3dc85331f5b0090` |
| Credential | `sha256:bdb02f07b34b264d96c05a28988bf35e4281d0dec3e3b85b3474bf9d01a4792e` |

Applicant's previous `3.0.0-rc.1` predates its circuit breaker. Its `rc.2`
contains the complete current code. SD's candidate adds caller-requested
instance removal; Credential's candidate follows its current `dev` release
tree. Existing version tags and `latest` were not overwritten.

## Reproduce the common integration check

From the common repository, with Docker, Python 3 and OpenSSL installed:

```bash
docker pull augustinploteanu/pad-gateway-service:2.0.0
python3 tests/verify_compose_gateway.py \
  --gateway-image augustinploteanu/pad-gateway-service:2.0.0 \
  --rules-image loredanaaaa/server-rules-service:2.0.0-rc.3 \
  --records-image loredanaaaa/university-record-service:2.0.0-rc.3 \
  --report docs/lab3-candidate-checks.json
```

The script uses the candidate defaults in this branch, with Player `3.0.0`,
Session `3.1.0`, DM `3.1.0` and Moderation `3.0.0`. It creates its own Compose
project, credentials, signing keys, volumes and loopback ports, then removes
that disposable project. It does not read or replace the project's `.env`.

The SD checks remove one Applicant registration, verify that the other
replica stays, repeat the removal safely, and re-register the instance before
the game checks. They test the registry API; they do not establish that
Gateway's breaker calls it.

## Verification result

The complete candidate run on 26 October 2026 passed **98 of 99 checks**.
The [machine-readable report](lab3-candidate-checks.json) records the exact
images and every result. All five new SD removal/re-registration checks
passed. The failing check is the existing **"a new Applicant reaches
University Record"**, which returned `404` instead of `200`.

Passing checks include replica registration and `/status`, private REST
boundaries, Gateway identity and role checks, real Applicant-to-Credential
handover, Session/DM WebSocket negotiation and handshakes, DM messages and
presence across replicas, Moderation decisions, Session-to-Player progression
and dynamic Moderation scaling/removal.

The run also exposed fresh-start timing issues. PostgreSQL health checks now
have a 60-second initialization grace period so a fresh database can finish its
final checkpoint before failures count toward the retry limit. The test waits
for a successful TCP probe as before; the grace period does not add a fixed
60-second delay to a ready database. The test waits
briefly for the separate advertised WS listeners after REST health succeeds;
it still requires `426` for ordinary HTTP. Startup failures print container
state/health details before cleanup, and successful startup prints the actual
Session/DM port mappings.

The test reserves exactly one WS port per replica, below the usual ephemeral
range. With a spare port, Docker was observed to leave the advertised first
port unused and assign the replicas later ports instead. Exact-size ranges
make that omission fail at startup rather than advertise an unbound URL.

## Remaining shared work

- University Record must accept and propagate the shared applicant story.
  Applicant and Credential then need `UNIVERSITY_RECORD_URL` wired through
  `gateway:8001/records`. It is deliberately unset in this Compose until that
  receiving endpoint is compatible.
- Gateway still uses Compose DNS upstreams. Part 3 must add SD-based
  round-robin, the breaker and caller-triggered removal with per-instance
  cooldown, plus `/status`, logs and registration with SD.
- Rules and Records still use the earlier `2.0.0-rc.3` images and one replica
  each; their owners must supply Lab 3 registration, status/logs and the
  appropriate outgoing-call breakers before scaling and monitoring cover all
  services.
- A real alert notification and the final presentation checks remain team
  work. This suite alone does not certify every Lab 3 grading criterion.

Track final release readiness in [CPR #45](https://github.com/georgerabus/PAD-team-20/issues/45).
