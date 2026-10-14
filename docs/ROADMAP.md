# BirdAlert Roadmap

## Current target

Complete Phase 1: a UK single-application product with 15-minute ingestion, unique processed sightings, a read API, and a simple public homepage. Phase 2 adds authenticated users and personalised email alerts.

The Bible's roadmap places the basic frontend at Sprint 5. It is included in the agreed Phase 1 product.

## Current repository state

Implemented in repository code/configuration: Milestone 1 configuration-driven polling, poller Lambda, eBird API request, SSM lookup, raw S3 write, supporting IAM and Terraform modules, Terraform remote-state bootstrap, and Milestone 2 scheduling/retention. Milestone 3 has S3-triggered processing, previous-15-minute window extraction, validation, and transformation. Milestone 4 persists accepted records to DynamoDB with conditional writes; a SHA-256 hash of submission ID and species code provides idempotency and deduplication, source regions are retained as provenance, entire private sightings are excluded, and otherwise well-formed unvalidated eBird records are marked provisional. Milestone 5 adds the public read API, database-aware health endpoint, timestamp-sorted query records, bounded cursor pagination, UK date conversion, and configurable API throttles. This does not confirm deployment to AWS.

Not implemented: homepage or explicit retry/failure handling. Processor logs already provide safe aggregate validation-rejection reasons; broader operational hardening remains Milestone 7.

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

## Milestone 3 - Processing window and validation (implemented in repository; not deployed)

- Extract only sightings relevant to the current 15-minute processing window from the 24-hour response.
- Define the minimum internal sighting fields: species, sighting timestamp, and location.
- Validate external record shape and reject malformed records from the internal model. Retain well-formed `obsValid: false` eBird records as provisional, with their validation status persisted and returned by the read API.
- Keep full raw payloads in S3; do not copy the whole response into the master database.
- Add focused tests for window selection, boundaries, and invalid records.

## Milestone 4 - Deduplication and master database (implemented in repository; not deployed)

- Define how sightings are identified as unique and make processing idempotent.
- Add the DynamoDB master database and persist only unique, well-formed processed sightings.
- Grant least-privilege access and test persistence/deduplication behavior.
- Exclude private sightings entirely from DynamoDB, superseding the earlier redaction-only implementation; keep complete raw responses in private S3.

## Milestone 5 - Read API (implemented in repository; not deployed)

- Add API Gateway and a Lambda read function.
- Provide recent sightings, species lookup, region lookup, and health endpoints; support retrieval by region, species, and date.
- Support combinations of region/species/date filters. Region means an eBird poll source code, retained as provenance.
- Use `GET /sightings` with optional `region`, `species`, `date`, `limit`, and `cursor`; return 10 latest sightings by default and at most 50. Species lookup filters sightings by eBird species code.
- Treat `date` as ISO 8601 `YYYY-MM-DD` in `Europe/London`, converting date boundaries to UTC for stored timestamps.
- Make the health endpoint verify the read function's database access.
- Configure initial API Gateway throttles of two requests per second with a burst of five for sightings, and one request per second with a burst of two for health. Keep values configurable in Terraform for later changes.
- The latest-sightings request queries the master database and returns the 10 most recent records.
- Add small timestamp-sorted DynamoDB query records for latest, region, species, and region-plus-species lookups. Keep one canonical record per unique sighting and never copy the raw payload into query records. Do not add a cache solely for the latest 10.
- Add focused API tests.

These scope decisions are accepted. Exact JSON response fields, status codes, cursor encoding, and query-record key values are implementation details to document with the Milestone 5 change. See [design decisions](DECISIONS.md).

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
