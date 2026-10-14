# BirdAlert Architecture

## Status

This document describes the intended architecture from `docs/BIBLE.md` and distinguishes it from the current repository implementation. It does not assert that AWS resources are deployed.

## Product boundary

BirdAlert is one public web application for UK sightings, not a generic multi-tenant service. Region codes are deployment configuration: the mechanism accepts one or more valid eBird codes, but the repository must not invent the deployer's definitive region list. Development may retain `GB-ENG`.

## Intended Phase 1 architecture

```text
EventBridge (15-minute heartbeat)
    -> Poll Lambda
    -> eBird API (previous 24 hours)
    -> S3 raw dump (region prefix; one-day lifecycle)
    -> validate / first-seen deduplicate
    -> DynamoDB master database (unique sightings)
    -> API Gateway
    -> read Lambda queries database per request
    -> browser / API clients

CloudFront -> private S3 site bucket (Origin Access Control) -> browser
```

The EventBridge schedule remains a 15-minute ingestion heartbeat, but the processor does not filter by the observation time in that interval. Each 24-hour response is validated, then a well-formed non-private sighting is persisted only when BirdAlert first sees its canonical identity. This captures public reports submitted after their observation time while avoiding repeated writes from overlapping eBird responses. Store the fields the application needs, at minimum species, sighting timestamp, location, validation status, and an internal `first_seen_at` ingestion timestamp on the canonical record. Keep the complete raw response in S3 rather than copying it wholesale into DynamoDB. Reject malformed records and make processing idempotent so the master database contains only unique sightings. Retain well-formed eBird records with `obsValid: false` as `provisional`, rather than misrepresenting them as validated.

Reject entire records marked `locationPrivate: true` before they enter the internal model or DynamoDB. The raw response remains intact in the private S3 bucket for its configured retention; privacy exclusion applies to processed storage and the public API.

The public homepage is plain static content in the repository's `site/` directory. Terraform deploys it to a dedicated private S3 site bucket; CloudFront, using Origin Access Control, is the public delivery layer and caches static assets. On each page load, the browser requests the API for the 10 most recent sightings and displays species, location, and timestamp. API Gateway invokes a read Lambda, which queries DynamoDB when requested. No user session, cookie, authentication, persistent latest-sightings cache, or background refresh is needed for Phase 1. CloudFront does not proxy or cache the API response; the API remains the source of current data.

The processor batch-reads canonical identities before creating records, so repeated 24-hour snapshots do not incur repeated transactional writes. Conditional canonical creation remains the concurrency guard. The processor writes one canonical item and four compact query items for a newly seen sighting; an already-known sighting from a new source region updates its provenance and only the two region-specific query items. The canonical item remains keyed by its sighting hash. Query items use the same table's `query-by-key` global secondary index: `LATEST`, `REGION#{region}`, `SPECIES#{species}`, and `REGION#{region}#SPECIES#{species}` are partition values, with `UTC observation timestamp#canonical sighting ID` as the descending sort key. This supports bounded queries without scans while retaining one authoritative canonical record. The exact processor trigger after the raw S3 write is intentionally unchanged.

## Storage and operations

Use one private S3 raw bucket with region-based prefixes and one separate private S3 site bucket. Configure lifecycle expiry for raw dumps; one day is the current configured retention, not an immutable constraint. CloudFront has access only to the site bucket through Origin Access Control. DynamoDB is the master database. Terraform provisions the infrastructure.

Use least-privilege IAM, Parameter Store for secrets/configuration, encryption where appropriate, input validation, structured logging, and observable, idempotent processing. Keep the design serverless, modular, and cost-conscious.

## Intended API

Provide `GET /sightings` and `GET /health`. `GET /sightings` provides recent sightings, species lookup, region lookup, and date retrieval through optional query parameters: `region`, `species`, `date`, `limit`, and `cursor`. Its default is the latest 10 results and its maximum page size is 50. The homepage uses this endpoint without filters and reads the database at request time. Species lookup filters sightings by eBird species code; a separate species catalogue is out of scope for Phase 1.

Region/species/date filters can be combined. Region is an eBird poll source code, retained in the item's `source_regions` set, not the AWS region. The `date` parameter uses ISO 8601 `YYYY-MM-DD` and denotes a calendar day in `Europe/London`; timestamps remain stored as UTC. This preserves a UK-first product boundary while leaving regional date/time semantics for a separately designed future change.

The API primarily serves BirdAlert's homepage. Because it is public and unauthenticated, other clients can call it directly; browser CORS restrictions do not authenticate callers. Start with configurable API Gateway throttles of two requests per second and a burst of five for sightings, and one request per second and a burst of two for health. Bound result pages to 50 records and use opaque cursors. API Gateway throttles are best-effort targets, not hard cost caps; these conservative values can be changed through Terraform after observing demand.

The health endpoint must perform a read against the master database using the read function's IAM role. A successful check verifies database access; it does not by itself prove ingestion is healthy or sightings are fresh. See [design decisions](DECISIONS.md) for the rationale and implementation status.

DynamoDB stores one canonical record per unique sighting. It also stores small query records with a timestamp-based sort key for the latest, region, species, and region-plus-species access patterns. The read Lambda queries the appropriate records rather than scanning the canonical dataset and filtering in memory. Query records carry only fields needed for that access pattern and never duplicate raw payloads. The processor uses DynamoDB transactions: it conditionally creates the canonical record and query records, or, on an existing canonical record, adds its source region and writes the applicable query records.

`GET /sightings` returns JSON with `sightings` and a nullable opaque `next_cursor`. Each sighting exposes its stable canonical ID, species code/names, UTC `observed_at`, `validation_status`, location ID/name/coordinates, and optional count. Invalid parameters return `400`; unknown routes return `404`; unavailable DynamoDB access returns `503`. `/health` returns `200` with database reachability when a lightweight DynamoDB read succeeds, otherwise `503`. These fields deliberately exclude submissions, source-region provenance, privacy flags, and raw upstream data.

## Phase 2 architecture

Cognito authenticates users; email is the username. Phase 2 retains the Bible's species/region watchlists and adds user data for registered location and an updatable radius in miles. Newly processed sightings are compared with the user's location and radius; matching sightings may trigger SNS email. Leave location representation, geolocation, distance calculation, and detailed Cognito schema to Phase 2 design. Phase 2 is not part of the Phase 1 deployment.

## Current implementation

The active implementation is substantially earlier than the intended Phase 1 architecture.

Implemented in repository configuration/code:

- Poll Lambda calling eBird and writing raw JSON to S3.
- Configurable comma-separated region codes and SSM parameter name supplied to Lambda by Terraform.
- Region-based, collision-resistant raw S3 object keys and visible per-region poll failures.
- EventBridge invokes the poller every 15 minutes, with scoped Lambda permission.
- Raw S3 objects and non-current versions expire after the configured one-day retention period.
- SSM Parameter Store lookup and Terraform modules for Lambda, IAM, parameter, and S3.
- Terraform bootstrap code for a remote-state bucket.
- Raw bucket versioning, encryption, and public-access blocking.
- S3-triggered processor Lambda with a raw-bucket read-only IAM role.
- A 180-second processor timeout so an initial first-seen backfill can complete without altering the low-cost serverless design; normal invocations are billed only for their actual duration.
- First-seen processing of validated 24-hour snapshots, minute- and second-precision timestamp parsing, and transformation into the internal sighting model.
- Processor completion logs include aggregate validation-rejection reason counts only; they do not log rejected records or raw sighting data.
- Focused tests for first-seen processing, invalid records, daylight-saving edge cases, S3-event handling, and repeat-write avoidance.
- DynamoDB master table with on-demand billing, server-side encryption, and point-in-time recovery.
- Batch identity checks and conditional transactional writes that make repeated deliveries idempotent and deduplicate by a SHA-256 hash of eBird submission ID and species code; canonical items retain their first ingestion timestamp.
- Source regions retained as provenance without participating in the sighting identity.
- Entire private-location sightings excluded before persistence, with a second guard at the DynamoDB write boundary; raw payloads remain in private S3.
- Well-formed `obsValid: false` records retained with a `provisional` validation status exposed through the read API.
- A DynamoDB global secondary index and minimal timestamp-sorted query records for latest, region, species, and combined lookups.
- Public HTTP API Gateway routes for `GET /sightings` and `GET /health`, a database-reading Lambda, opaque cursor pagination, validated UK-calendar date filtering, and Terraform-configured route throttles.
- Focused tests for read queries, date conversion, cursor validation, health connectivity, and API errors.

Not implemented in the active configuration/code:

- Latest-10 homepage or frontend.

Focused tests cover poller configuration/failure/key behavior, processor handling, persistence, deduplication, private-location exclusion, and the read API.

## Known mismatches

- The dev tfvars configures `GB-ENG`; deployment region values are not hard-coded in application code.
- The root Terraform backend has a fixed dev state key despite dev and prod variable files.
- The raw bucket name includes a stable Terraform-generated eight-character hexadecimal suffix to reduce global S3 naming collisions. Terraform module outputs supply the resulting name and ARN to dependent Lambda configuration, IAM policies, and S3 notification resources. The established remote-state bucket retains its existing six-character suffix because changing the backend bucket would require replacement and state migration.
- The README describes capabilities that are not yet implemented.

These are known gaps, not reasons to redesign the product. See `docs/ROADMAP.md` for milestones.
