# BirdAlert design decisions

This record preserves agreed choices and their rationale for project review. `BIBLE.md` remains the authoritative specification; `ROADMAP.md` distinguishes implementation from future work. Git history preserves changes to these documents.

## 2026-10-14 - Private sightings excluded entirely

Accepted and implemented locally. A record marked `locationPrivate: true` is excluded before transformation into the internal model and is blocked again at the DynamoDB write boundary. Missing or non-boolean privacy flags also fail validation. Rejection reporting uses counts and generic reasons, not private sighting details.

Rationale: BirdAlert uses volunteer contributions and must respect their privacy choices even when an upstream endpoint returns the record. Keeping a redacted sighting still retains information about that contribution, so entire-record exclusion replaces the earlier redaction-only policy.

Complete raw responses remain in the access-restricted S3 landing bucket for their configured retention, as required by the Bible. They are not exposed by the read API. This change prevents new private records entering DynamoDB; any previously persisted private records would require separately reviewed cleanup. No AWS cleanup is performed by this change.

## 2026-10-14 - Provisional eBird sightings retained with explicit status

Accepted and implemented locally. Well-formed eBird records with `obsValid: false` enter the internal model and DynamoDB with `validation_status: "provisional"`; records with `obsValid: true` are marked `"validated"`. The read API returns this status so clients do not mistake a provisional report for a validated one. `obsValid` must still be a boolean, and malformed records remain rejected.

Rationale: the UK notable-feed test run contained predominantly provisional records. Excluding them made the MVP unable to demonstrate its end-to-end ingestion, storage, and API flow. The project deliberately prioritises demonstrating a responsible AWS and agentic-development workflow while preserving an honest data-quality signal for the client and future refinements. This is not a claim that provisional sightings have been confirmed.

Private-location exclusion remains unchanged: `locationPrivate: true` records are never persisted or exposed. The change is intentionally limited to eBird's validation marker, not contributor privacy.

The processor now accepts eBird timestamps with minute or second precision. Date-only timestamps remain rejected in Phase 1 because they cannot be sorted or presented with a truthful observation time; their treatment is deferred for later design.

## 2026-10-14 - First-seen ingestion from overlapping eBird snapshots

Accepted and implemented locally. EventBridge continues to invoke the poller every 15 minutes and eBird continues to return the preceding 24 hours. The processor validates every snapshot but persists a well-formed non-private sighting only when its canonical identity has not previously been recorded by BirdAlert. The canonical DynamoDB item records the raw-object ingestion time as `first_seen_at`; public query records continue to sort by the actual `observed_at` timestamp.

Before writing, the processor uses DynamoDB `BatchGetItem` to identify canonical sightings already present, then conditionally transaction-writes only new canonical and query records. The conditional write remains the concurrency safeguard. If an already-known sighting arrives through a new eBird source region, the processor updates its provenance and the two region-specific query records without rewriting the global latest or species records.

Rationale: eBird reports can be submitted long after their observation time, so filtering the 24-hour response to the last 15 minutes excluded most public sightings and made the application appear stale. First-seen ingestion captures those reports while preserving the EventBridge heartbeat, Lambda and S3 event-driven flow that demonstrates the intended AWS architecture. Batch identity reads keep overlapping snapshots from causing repeated transactional writes, reducing DynamoDB cost without adding a cache, service, or operational burden. `first_seen_at` preserves an operational audit trail while `observed_at` remains the truthful user-facing ordering.

Privacy is unchanged: `locationPrivate: true` records remain excluded before any internal persistence, and date-only timestamps remain outside Phase 1 until their product treatment is explicitly designed.

The processor Lambda timeout is set to 180 seconds. This protects the first execution, when a full 24-hour snapshot can legitimately introduce many canonical sightings, while preserving pay-for-use Lambda billing; it does not reserve capacity or make normal quick invocations cost more.

## 2026-10-14 - Region means eBird poll source region

Accepted and implemented locally. API region filters refer to the eBird region code used to poll sightings, such as the configured development code `GB-ENG`. A sighting can retain multiple source regions when overlapping polls return it. Region does not participate in sighting identity and is unrelated to the AWS deployment region.

Rationale: using the source's region vocabulary keeps ingestion and retrieval consistent and preserves room for future expansion. The MVP remains UK-only; future international coverage would need additional design, including observation timezone handling.

## 2026-10-14 - App-focused public API with combined filters

Accepted and implemented locally. The read API primarily serves BirdAlert's homepage using processed sightings accumulated in DynamoDB. It does not serve raw eBird dumps or poll eBird on each client request. The upstream 24-hour response window and raw S3 retention do not impose a 24-hour retention limit on processed DynamoDB sightings; the table currently has no expiry.

Region, species, and date filters may be combined. `GET /sightings` accepts optional `region`, `species`, `date`, `limit`, and `cursor` parameters. It returns 10 latest sightings by default and permits at most 50 records in one page. Species lookup means filtering sightings by eBird species code; a separate species catalogue is not part of Phase 1. Public unauthenticated access also allows direct requests from other clients, so app ownership cannot be enforced simply by hiding the endpoint or restricting browser CORS origins.

Rationale: combined filters support useful app queries while a 50-result maximum bounds DynamoDB work and response size. API Gateway starts at two requests per second with a burst of five for sightings, and one request per second with a burst of two for health. These Terraform-managed values can increase with observed demand. API Gateway throttles are best-effort targets, not guaranteed request ceilings or spending caps. No new protection service is selected here.

## 2026-10-14 - UK calendar-date API filter

Accepted and implemented locally. The `date` query parameter is ISO 8601 `YYYY-MM-DD` and selects a calendar day in `Europe/London`. DynamoDB retains timestamps in UTC, and the read Lambda converts the start and end of the requested UK day to UTC before querying.

Rationale: BirdAlert is UK-first, so human-facing date queries should align with UK calendar days, including daylight-saving transitions. ISO `YYYY-MM-DD` is intentionally unambiguous across locales. Any future support for regional date/time semantics must be explicit, versioned or opt-in, and designed alongside international expansion; Phase 1 does not accept ambiguous US-style date inputs.

## 2026-10-14 - Canonical sightings and DynamoDB query records

Accepted and implemented locally. DynamoDB retains one canonical record per unique sighting. Small query records with timestamp sort keys support the latest, region, species, and region-plus-species access patterns. They contain only fields required to answer the corresponding read request and never copy a raw eBird payload. A single `query-by-key` global secondary index uses query keys `LATEST`, `REGION#{region}`, `SPECIES#{species}`, and `REGION#{region}#SPECIES#{species}`; its timestamp-prefixed sort key makes reverse-order DynamoDB queries efficient. The processor batch-checks canonical identities, conditionally creates the canonical record with its four query records only when first seen, and skips a repeat from an existing source region. A duplicate from a new source region updates provenance and only that region's two query records.

Rationale: the canonical record is the authoritative stored sighting. Purpose-built query records make the public API's bounded reads predictable and avoid costly table scans or a separate cache. The exact key shape, transactional write strategy, cursor encoding, and response projection remain Milestone 5 implementation details.

## 2026-10-14 - Health verifies database access

Accepted and implemented locally. The health endpoint verifies that the read function can reach and read from the master DynamoDB table using its normal credentials and permissions.

Rationale: function liveness alone can report success while the application's database access is broken, which is misleading during troubleshooting. The check reports database accessibility; ingestion freshness is a separate concern. It returns `200` with database reachability after a successful lightweight `GetItem`, and `503` when that read fails.

## 2026-10-14 - Raw bucket naming suffix

Accepted and implemented locally. The raw bucket name now includes a stable Terraform-generated eight-character hexadecimal suffix. The suffix is created once and retained in Terraform state, so dependent configuration receives a consistent bucket name.

Rationale: S3 bucket names occupy a global namespace. The suffix substantially reduces naming-collision risk while retaining meaningful project and environment components. It does not guarantee availability.

The raw bucket module's outputs supply its resulting name and ARN to the poller, processor, IAM policies, and S3 notification resources. The established Terraform state bucket retains its existing six-character suffix because changing the backend bucket would require replacement and state migration. Applying this raw-bucket change to an existing environment will replace that bucket; review the Terraform plan before applying.
