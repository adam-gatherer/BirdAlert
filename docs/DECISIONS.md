# BirdAlert design decisions

This record preserves agreed choices and their rationale for project review. `BIBLE.md` remains the authoritative specification; `ROADMAP.md` distinguishes implementation from future work. Git history preserves changes to these documents.

## 2026-10-14 - Private sightings excluded entirely

Accepted and implemented locally. A record marked `locationPrivate: true` is excluded before transformation into the internal model and is blocked again at the DynamoDB write boundary. Missing or non-boolean privacy flags also fail validation. Rejection reporting uses counts and generic reasons, not private sighting details.

Rationale: BirdAlert uses volunteer contributions and must respect their privacy choices even when an upstream endpoint returns the record. Keeping a redacted sighting still retains information about that contribution, so entire-record exclusion replaces the earlier redaction-only policy.

Complete raw responses remain in the access-restricted S3 landing bucket for their configured retention, as required by the Bible. They are not exposed by the read API. This change prevents new private records entering DynamoDB; any previously persisted private records would require separately reviewed cleanup. No AWS cleanup is performed by this change.

## 2026-10-14 - Region means eBird poll source region

Accepted; ingestion provenance is already implemented, API queries remain pending. API region filters refer to the eBird region code used to poll sightings, such as the configured development code `GB-ENG`. A sighting can retain multiple source regions when overlapping polls return it. Region does not participate in sighting identity and is unrelated to the AWS deployment region.

Rationale: using the source's region vocabulary keeps ingestion and retrieval consistent and preserves room for future expansion. The MVP remains UK-only; future international coverage would need additional design, including observation timezone handling.

## 2026-10-14 - App-focused public API with combined filters

Accepted for Milestone 5; not implemented. The read API primarily serves BirdAlert's homepage using validated sightings accumulated in DynamoDB. It does not serve raw eBird dumps or poll eBird on each client request. The upstream 24-hour response window and raw S3 retention do not impose a 24-hour retention limit on processed DynamoDB sightings; the table currently has no expiry.

Region, species, and date filters may be combined. Public unauthenticated access also allows direct requests from other clients, so app ownership cannot be enforced simply by hiding the endpoint or restricting browser CORS origins.

Rationale: combined filters support useful app queries while conservative request/burst throttling and bounded database reads reduce abuse and cost. API Gateway throttles are best-effort targets, not guaranteed request ceilings or spending caps. Exact endpoint shapes, date/timezone semantics, result limits, pagination, throttle values, and query/index design remain pending the API discussion; no new protection service is selected here.

## 2026-10-14 - Health verifies database access

Accepted for Milestone 5; not implemented. The health endpoint must verify that the read function can reach and read from the master DynamoDB table using its normal credentials and permissions.

Rationale: function liveness alone can report success while the application's database access is broken, which is misleading during troubleshooting. The check reports database accessibility; ingestion freshness is a separate concern. Exact response shape and status codes remain pending the API discussion.

## 2026-10-14 - Raw bucket naming proposal

Pending human confirmation. The raw bucket currently derives its name from project/environment, with no random suffix. The Terraform state bootstrap uses a separate six-character hexadecimal suffix.

The proposed raw bucket name includes a stable Terraform-generated eight-character lowercase alphanumeric suffix to reduce global S3 naming collisions. Randomness reduces collision risk rather than guaranteeing availability. Changing the name of an existing bucket requires replacement; a plan must be reviewed before applying any such change. No naming change is included in this work.
