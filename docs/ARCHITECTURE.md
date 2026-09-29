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
    -> extract current 15-minute slice
    -> validate / process / deduplicate
    -> DynamoDB master database (unique sightings)
    -> API Gateway
    -> read Lambda queries database per request
    -> public homepage / API clients
```

The processor must select the current 15-minute window from each 24-hour response, not load the entire response into the master database. Store the fields the application needs, at minimum species, sighting timestamp, and location. Keep the complete raw response in S3 rather than copying it wholesale into DynamoDB. Reject invalid records and make processing idempotent so the master database contains only unique sightings.

The public homepage requests the read API for the 10 most recent sightings and displays species, location, and timestamp. API Gateway invokes a read Lambda, which queries DynamoDB when requested. No user session, cookie, authentication, or persistent latest-sightings cache is needed for Phase 1. Frontend refresh every 15 minutes is optional. Do not add caching infrastructure absent a measured need.

The database key/index pattern for the latest-10 query is an implementation decision for the API milestone. The exact processor trigger after the raw S3 write is also not prescribed here and should be decided in that milestone without changing the product flow.

## Storage and operations

Use one S3 raw bucket with region-based prefixes. Configure lifecycle expiry for raw dumps; one day is the current configured retention, not an immutable constraint. DynamoDB is the master database. Terraform provisions the infrastructure.

Use least-privilege IAM, Parameter Store for secrets/configuration, encryption where appropriate, input validation, structured logging, and observable, idempotent processing. Keep the design serverless, modular, and cost-conscious.

## Intended API

Provide read-only endpoints for recent sightings, species lookup, region lookup, and health. Support retrieval by region, species, and date. The homepage's latest-10 request uses the same read API and reads the database at request time.

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

Not implemented in the active configuration/code:

- Current-15-minute extraction, validation, transformation, or deduplication.
- DynamoDB master database or processing function.
- Read API, API Gateway, latest-10 homepage, or frontend.

Focused tests now cover the poller configuration and failure/key behavior. The repository still has empty placeholder areas for API, transformer, and validation.

## Known mismatches

- The dev tfvars configures `GB-ENG`; deployment region values are not hard-coded in application code.
- The root Terraform backend has a fixed dev state key despite dev and prod variable files.
- The README describes capabilities that are not yet implemented.

These are known gaps, not reasons to redesign the product. See `docs/ROADMAP.md` for milestones.
