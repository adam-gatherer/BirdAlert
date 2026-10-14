# BirdAlert Requirements

## Product boundary

BirdAlert is a single deployed public web application for the UK, not a generic multi-tenant platform. It demonstrates AWS, Terraform/IaC, DevOps, production-quality engineering, and responsible use of AI development tools. Requirements below are derived from `docs/BIBLE.md`.

## Phase 1 functional requirements

The system shall:

1. Run a polling heartbeat every 15 minutes.
2. Support one or more valid eBird region codes supplied as deployment configuration. Development may configure `GB-ENG`; the repository must not invent a definitive deployment region list.
3. Retrieve the eBird previous-24-hour response for each configured region.
4. Store each complete raw response in one S3 bucket using region-based prefixes.
5. Apply lifecycle expiry to raw dumps. One day is the current configured retention, configurable rather than an immutable architecture requirement.
6. Validate each previous-24-hour response and persist a well-formed non-private sighting only when BirdAlert first sees its canonical identity. The 15-minute schedule is an ingestion heartbeat, not an observation-time filter; do not copy the full raw response to the master database.
7. Validate external record shape and reject malformed records from the internal model. Accept eBird records with `obsValid: false` as well-formed provisional sightings, retaining a `validation_status` marker.
8. Transform well-formed records into an internal model and deduplicate them so the master database contains only unique sightings.
9. Store at minimum species, sighting timestamp, sighting location, validation status, and canonical `first_seen_at` ingestion timestamp in the master database. Do not unnecessarily duplicate the full raw payload there.
10. Make processing idempotent.
11. Provide `GET /sightings` for recent sightings, species lookup, region lookup, and retrieval by region, species, and date, including combinations of these filters. It accepts optional `region`, `species`, `date`, `limit`, and `cursor` parameters; defaults to 10 results; and limits pages to 50. Region refers to the configured eBird region used to obtain a sighting, not the AWS deployment region. Species lookup filters sightings by eBird species code.
12. Provide a public static homepage from a dedicated private S3 site bucket through CloudFront Origin Access Control. It obtains the 10 most recent sightings with species, location, and timestamp through one read-API request on page load; it does not refresh in the background.
13. Have the latest-sightings endpoint query the master database when requested. Do not require sessions, cookies, authentication, persistent latest-10 caching, Redis, ElastiCache, or a heartbeat-written cache for the public Phase 1 homepage.
14. Exclude entire records marked `locationPrivate: true` from the internal model and master database. Preserve complete raw responses only in the private S3 landing area for their configured retention.
15. Have the health endpoint check the read function's connectivity and permission to access the master database, rather than returning function liveness alone.
16. Interpret `date` as ISO 8601 `YYYY-MM-DD` for a calendar day in `Europe/London`, converting the requested range to UTC for stored timestamps. Do not accept ambiguous regional date formats in Phase 1.
17. Record the completion time of each successfully processed raw response and return it as a nullable `last_successful_processing_at` field from `GET /sightings`; the homepage shall display it as the data-freshness indicator. This is not a cached sightings copy or browser-generated timestamp.

The exact database key/index access pattern for the latest-10 query is an implementation concern for the read API milestone, not an additional product requirement. The homepage reads on page load only; backend correctness must not rely on a cached homepage copy.

## Security requirements

The system shall:

- use least-privilege IAM;
- use Parameter Store for secrets and configuration;
- encrypt storage where appropriate;
- validate external input;
- avoid credentials in source code;
- use structured logging and preserve raw responses in S3 for their configured retention period.
- apply configurable conservative request/burst throttling to the public API and bound database work per request to reduce abuse and cost; throttling is not a guaranteed request ceiling or spending cap.
- initially configure API Gateway throttles at two requests per second with a burst of five for sightings, and one request per second with a burst of two for health. Keep these values in Terraform configuration for later adjustment.
- answer read requests through timestamp-sorted DynamoDB query records rather than scans, and keep any query-record projection minimal.

## Non-functional requirements

The system should be serverless-first, observable, modular, idempotent, low-cost, and easily extensible.

## Phase 2 requirements

Phase 2 introduces:

- Cognito authentication, with email address as the username;
- user-maintained watchlists containing species and region, as specified by the Bible;
- user data containing email, registered location, and a user-updatable alert radius expressed as “within X miles of me”;
- matching newly processed sightings against each user's configured location and radius;
- optional email alerts for sightings within that radius, using SNS as specified by the Bible.

Location representation/storage, geolocation implementation, distance calculation, and detailed Cognito schema are intentionally deferred to Phase 2 design.

## Out of scope

Multi-tenancy, analytics, AI product features, mobile applications, advanced administration, social features, and complex recommendation systems. Phase 2 features are out of Phase 1 scope.

## Current implementation status

The repository currently has a poller Lambda with Terraform-supplied region and SSM configuration, a 15-minute EventBridge heartbeat, one-day raw S3 lifecycle expiry, region-prefixed raw S3 writes, and an S3-triggered processor Lambda. The processor validates each 24-hour snapshot and uses first-seen canonical identities to persist the internal model to DynamoDB. A SHA-256 hash of eBird submission ID and species code provides idempotency and deduplication; a batch identity check avoids repeat transactional writes, source regions are retained as provenance, private sightings are excluded entirely before persistence, and unvalidated eBird sightings are retained as provisional. A fixed-key status item records successful processing completion for the homepage freshness indicator. The public read API, database-aware health check, bounded pagination, UK-calendar date filtering, least-privilege read role, and Terraform-configured throttles are implemented locally. The local static homepage makes one page-load request to that API and is configured for private-S3/CloudFront deployment. These are status observations, not reductions to the requirements.
