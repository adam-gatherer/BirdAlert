# BirdAlert Roadmap

## Current target

Complete Phase 1: a UK single-application product with 15-minute ingestion, unique processed sightings, a read API, and a simple public homepage. Phase 2 adds authenticated users and personalised email alerts.

The Bible's roadmap places the basic frontend at Sprint 5. It is included in the agreed Phase 1 product.

## Current repository state

Implemented in repository code/configuration: Milestone 1 configuration-driven polling, poller Lambda, eBird API request, SSM lookup, raw S3 write, supporting IAM and Terraform modules, Terraform remote-state bootstrap, and Milestone 2 scheduling/retention. Milestone 3 has S3-triggered first-seen processing of 24-hour snapshots, validation, and transformation. Milestone 4 persists accepted records to DynamoDB with conditional writes; a SHA-256 hash of submission ID and species code provides idempotency and deduplication, batch identity checks avoid repeat transactional writes, source regions are retained as provenance, entire private sightings are excluded, and otherwise well-formed unvalidated eBird records are marked provisional. Milestone 5 adds the public read API, database-aware health endpoint, timestamp-sorted query records, bounded cursor pagination, UK date conversion, and configurable API throttles. Milestone 6 adds the static homepage, private S3/CloudFront delivery, API configuration, and focused frontend tests. Milestone 6.5 adds a processor-completion freshness timestamp. This does not confirm deployment to AWS.

Not implemented: explicit retry/failure handling. Processor logs already provide safe aggregate validation-rejection reasons; broader operational hardening remains Milestone 7.

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

## Milestone 3 - First-seen processing and validation (implemented in repository; not deployed)

- Treat the 15-minute EventBridge schedule as an ingestion heartbeat, not an observation-time filter.
- Validate each 24-hour response and accept a well-formed non-private sighting when BirdAlert first sees its canonical identity.
- Define the minimum internal sighting fields: species, sighting timestamp, and location.
- Validate external record shape and reject malformed records from the internal model. Retain well-formed `obsValid: false` eBird records as provisional, with their validation status persisted and returned by the read API.
- Keep full raw payloads in S3; do not copy the whole response into the master database.
- Add focused tests for first-seen processing, repeat snapshots, and invalid records.

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

## Milestone 6 - Public homepage (implemented in repository; not deployed)

- Add plain static homepage assets under `site/` that request the 10 most recent sightings from the read API when the page loads and display species, location, and timestamp.
- Deploy the site through Terraform to a dedicated private S3 site bucket, delivered publicly through CloudFront Origin Access Control.
- Configure the API's CORS origin for the CloudFront site; do not proxy or cache the API response through CloudFront.
- Do not add authentication, sessions, cookies, background refresh, persistent application caching, or a heartbeat-written cache for the public Phase 1 homepage.

## Milestone 6.5 - Data freshness visibility (implemented in repository; not deployed)

- After successfully processing a raw S3 object, write its completion time to one fixed-key DynamoDB operational-status item.
- Return nullable `last_successful_processing_at` from `GET /sightings` and display it on the homepage in UK time.
- Do not treat poll initiation, browser load time, or a successful poll that has not completed processing as evidence that displayed data is fresh.
- Do not add a cache, new AWS service, table schema change, or background browser polling for this indicator.

## Milestone 7 - Operational hardening

- Add three bounded exponential-backoff retries for transient eBird network, `429`, and `5xx` failures; do not retry invalid data or non-transient client errors.
- Add separate encrypted 14-day SQS DLQs for exhausted poller and processor deliveries. Keep replay manual in Phase 1.
- Add 30-day CloudWatch log retention and high-priority alarms for poller/processor errors, DLQ messages, sustained API `5xx` errors, and no successful processor completion for 45 minutes.
- Publish alarms to an SNS operational topic. Make the administrator email subscription optional Terraform configuration; do not notify on routine successful 15-minute heartbeats.
- Review IAM, encryption, raw retention, environment configuration, and deployment procedure.
- Add focused failure/retry and Terraform tests; run relevant local validation and report live AWS state only if actually checked.

## Phase 2 - Users and personalised alerts

After Phase 1, implement Cognito authentication (email as username), species/region watchlists, user email/location/updatable radius in miles, matching of newly processed sightings against that radius, and SNS email alerts. Decide location representation, geolocation, distance calculation, and Cognito schema during Phase 2 design. Do not build these features into Phase 1.
