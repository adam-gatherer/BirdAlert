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
6. Extract only sightings relevant to the current 15-minute processing window; do not copy the full 24-hour response to the master database.
7. Validate external records and reject invalid records from the internal model.
8. Transform valid records into an internal model and deduplicate them so the master database contains only unique sightings.
9. Store at minimum species, sighting timestamp, and sighting location in the master database. Do not unnecessarily duplicate the full raw payload there.
10. Make processing idempotent.
11. Provide a read-only API for recent sightings, species lookup, region lookup, health, and retrieval by region, species, and date.
12. Provide a public homepage that obtains data through the read API and displays the 10 most recent sightings with species, location, and timestamp.
13. Have the latest-sightings endpoint query the master database when requested. Do not require sessions, cookies, authentication, persistent latest-10 caching, Redis, or ElastiCache for the public Phase 1 homepage.

The exact database key/index access pattern for the latest-10 query is an implementation concern for the read API milestone, not an additional product requirement. A frontend refresh every 15 minutes is optional; backend correctness must not rely on a cached homepage copy.

## Security requirements

The system shall:

- use least-privilege IAM;
- use Parameter Store for secrets and configuration;
- encrypt storage where appropriate;
- validate external input;
- avoid credentials in source code;
- use structured logging and preserve raw responses in S3 for their configured retention period.

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

The repository currently has a poller Lambda with Terraform-supplied region and SSM configuration, a 15-minute EventBridge heartbeat, one-day raw S3 lifecycle expiry, region-prefixed raw S3 writes, and an S3-triggered processor Lambda. The processor extracts the previous 15-minute window, validates external records, and conditionally persists the internal model to DynamoDB. A SHA-256 hash of eBird submission ID and species code provides idempotency and deduplication; source regions are retained as provenance and private locations are redacted before persistence. Read API and homepage remain unimplemented. These are status observations, not reductions to the requirements.
