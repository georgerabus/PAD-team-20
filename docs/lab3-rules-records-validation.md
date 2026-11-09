# Lab 3 validation — 29 October 2026

User-run Docker verification with local images pad-rules:lab3,
pad-records:lab3 and pad-gateway:lab3:

- Two healthy replicas per owned service, distinct instanceId values and integer load fields.
- SD registered two hostname addresses for rules and two for records.
- SD restart recovered all four registrations without restarting web replicas.
- Rules scaling 2 -> 3 -> 2 added and removed the corresponding SD registration.
- Six requests through Gateway internal port alternated A/B for each service.
- Eight Gateway automated tests passed inside its Python 3.13 image with pinned dependencies.
- Two live breaker runs: six 502 responses (three per stopped instance), then
  503 SERVICE_UNAVAILABLE. Both TRIP and SD removal verified. Original containers
  restarted and traffic recovered after registration/cooldown.
- Disposable fresh PostgreSQL startup with two replicas each passed migration
  and readiness checks; migration entries were not duplicated.
- Twelve concurrent Rules writes had distinct versions; both replicas read the same latest version.
- Twelve independent Records bootstrap requests produced twelve distinct applicants,
  visible from both replicas, as required by the retained bootstrap contract.
- Concurrent legacy consumer calls deduplicated eventId and applicantId across replicas.

Limits: no claim of full HTTP ApplicantStory integration, no load-alert stress
result, no public-port end-to-end authentication regression run with the new
Gateway, and no new image publication. Fresh startup is useful concurrency
evidence, not an exhaustive proof against every possible migration schedule.

Current CPR dev has no broker/workers. Preserve that architecture. Private
repositories still contain legacy event code; the Records HTTP handover debt
is separate. Do not stage unrelated submodule state or restore old Compose
from stash over current dev.

## Published candidate follow-up

The owner published the tested feature commits without merging main/dev or
updating latest. The publication script confirmed linux/amd64 and linux/arm64.

- loredanaaaa/server-rules-service:3.0.0-rc.1 — source 03d88c9;
  manifest index sha256:2ee36a53cd5bed58380630d3c8c259d11f48bf475df65281f63e6727d4d1f7b2.
- loredanaaaa/university-record-service:3.0.0-rc.1 — source a855ba4;
  manifest index sha256:c5243c084b297f131cbb39d311febeb00dd27016f34dcecf45f14670ea0fb22c.

.env.example now selects these candidates. Existing .env files and shell
variables must be updated explicitly. Runtime follow-up with the published images passed on 29 October 2026:
all four containers were healthy after pulling the candidate tags. Four requests
per service through the local Lab 3 Gateway alternated A/B/A/B. Rules instance
IDs were bf8b209204bf and 0192028ded53; Records IDs were db65f71b649e and
a708265206a2. Both reported integer load fields (0/16). Other earlier runtime
checks used local Lab 3 images.
Gateway publication remains separate; its example tag has not been changed.


## Published Gateway follow-up (29 October 2026)

Gateway PR #10 was merged into dev (owner screenshot). Candidate
loredanaaaa/pad-gateway-service:lab3-f39a4a2 contains source f39a4a2;
manifest index sha256:fe67a9cc5aa60458c877fc534e1da28910fb1d41b78d6ed6a9ac71b5bf9310a3.
Publication verified linux/amd64 and linux/arm64. .env.example now selects it.

All 13 routing/breaker/request-logging tests passed in Docker. The regression
confirms peer-returned 502 responses do not evict healthy Session replicas;
actual Gateway transport failures still count, as do timeouts and peer 503.

Owner-provided live output confirms the published Gateway is healthy, four
requests per service alternate between the two published Rules/Records replicas,
and REQUEST logs contain method, path, status, durationMs, port and completed.
The live failure test produced six transport 502 responses, followed by explicit
503; both Rules instances tripped and were removed from SD. The test restored
both original containers and confirmed registrations and service recovery.

These checks do not establish full-stack HTTP ApplicantStory delivery, WebSocket
instance affinity, or SD cache/fallback support. Those limitations remain.
