# BirdAlert Roadmap

## Current target

Complete Phase 1: a UK single-application product with 15-minute ingestion, unique processed sightings, a read API, and a simple public homepage. Phase 2 adds authenticated users and personalised email alerts.

The Bible's roadmap places the basic frontend at Sprint 5. It is included in the agreed Phase 1 product.

## Current repository state

Implemented in repository code/configuration: Milestone 1 configuration-driven polling, poller Lambda, eBird API request, SSM lookup, raw S3 write, supporting IAM and Terraform modules, and Terraform remote-state bootstrap. This does not confirm deployment to AWS.

Not implemented: current-window extraction, validation, transformation, deduplication, DynamoDB master database, read API, homepage, structured logging, or explicit retry/failure handling.

The poller configuration interface is `EBIRD_REGIONS` (comma-separated region codes), `PARAMETER_NAME` (environment-specific SSM parameter name), and `RAW_BUCKET`. Terraform supplies these Lambda environment variables. `terraform/environments/dev.tfvars` configures `GB-ENG`; deployment-specific region values remain the deployer's responsibility.

## Milestone 1 - Configuration-driven polling (implemented in repository; not deployed)

Remove hard-coded region and environment assumptions from the poller.

- Configure one or more valid eBird region codes through Terraform/application configuration. The deployer supplies deployment-specific values; do not invent a definitive region list. Development may continue to use `GB-ENG`.
- Supply the environment-specific SSM parameter name through configuration.
- Pass runtime configuration to Lambda through environment variables unless an established project pattern is clearly better.
- Keep production infrastructure out of scope.
- Poll each configured region and associate each response with its source region.
- Use a region-based S3 prefix and a collision-resistant key that identifies region and ingestion event.
- Store the complete successful raw JSON response. Surface HTTP, network, invalid JSON, and S3 write failures; do not report a region as successful if its operation failed.
- Do not add record validation, transformation, deduplication, scheduling, or complex retries in this milestone.

Acceptance: configuration supports one and multiple regions; dev continues to use `GB-ENG`; parameter path is not hard-coded; raw keys are region-prefixed and cannot collide within one second; successful responses are stored completely; failures are visible; focused tests cover configuration and key generation; Terraform is formatted/validated; docs describe the interface; no unrelated changes or secrets are introduced.

## Milestone 2 - 15-minute heartbeat and raw retention (implemented in repository; not deployed)

- Add the EventBridge 15-minute heartbeat and Lambda invocation permission.
- Preserve the previous-24-hour eBird dump in the single raw S3 bucket with region prefixes.
- Add configurable S3 lifecycle expiry. One day is the current configured retention, not an immutable architecture constraint.
- Verify behavior without deploying or modifying production infrastructure.

## Milestone 3 - Processing window and validation

- Extract only sightings relevant to the current 15-minute processing window from the 24-hour response.
- Define the minimum internal sighting fields: species, sighting timestamp, and location.
- Validate external records and reject invalid records from the internal model.
- Keep full raw payloads in S3; do not copy the whole response into the master database.
- Add focused tests for window selection, boundaries, and invalid records.

## Milestone 4 - Deduplication and master database

- Define how sightings are identified as unique and make processing idempotent.
- Add the DynamoDB master database and persist only unique, valid processed sightings.
- Grant least-privilege access and test persistence/deduplication behavior.

## Milestone 5 - Read API

- Add API Gateway and a Lambda read function.
- Provide recent sightings, species lookup, region lookup, and health endpoints; support retrieval by region, species, and date.
- The latest-sightings request queries the master database and returns the 10 most recent records.
- Decide the DynamoDB key/index access pattern needed for that query during this milestone. Do not add a cache solely for the latest 10.
- Add focused API tests.

## Milestone 6 - Public homepage

- Build a simple homepage that requests the read API and displays the 10 most recent sightings with species, location, and timestamp.
- Do not add authentication, sessions, cookies, or persistent application caching for the public Phase 1 homepage.
- A 15-minute frontend refresh is optional; backend behavior must not depend on a cached homepage copy.

## Milestone 7 - Operational hardening

- Add structured logging and deliberate failure/retry behavior.
- Review IAM, encryption, raw retention, environment configuration, and deployment procedure.
- Run relevant local tests and safe validation; report live AWS state only if actually checked.

## Phase 2 - Users and personalised alerts

After Phase 1, implement Cognito authentication (email as username), species/region watchlists, user email/location/updatable radius in miles, matching of newly processed sightings against that radius, and SNS email alerts. Decide location representation, geolocation, distance calculation, and Cognito schema during Phase 2 design. Do not build these features into Phase 1.
