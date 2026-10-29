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
