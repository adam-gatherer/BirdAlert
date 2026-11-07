# BirdAlert Bible

## Vision and purpose

BirdAlert is a real, single deployed web application for the UK. It ingests notable bird sightings from the eBird API, stores a reusable internal model, exposes sightings through an API and homepage, and later delivers personalised alerts.

The project demonstrates AWS, Terraform/IaC, DevOps practices, production-quality software engineering, and responsible use of modern AI development tools. It is one application, not a generic multi-tenant platform.

## Goals

Build a serverless-first, modular, observable, low-operational-cost application using AWS and Infrastructure as Code. Keep the design simple and extensible.

## Phase 1 scope

Implement the complete ingestion, read API, and simple homepage:

- A 15-minute heartbeat polls configured eBird regions. Deployment configuration supplies one or more valid eBird region codes; development may use `GB-ENG`. Do not assume or embed a definitive deployment region list.
- Request the previous day of UK sightings from eBird explicitly with `back=1`. Each poll stores the complete raw response in one S3 bucket, under a region-based prefix.
- S3 is the raw landing area. The current lifecycle configuration retains raw data for one day; this remains a deployment/configuration choice, not an immutable architecture constraint.
- Processing validates each 24-hour response and persists a non-private sighting only when BirdAlert first sees its canonical identity. The 15-minute EventBridge cadence remains the ingestion heartbeat; it is not an observation-time filter. It must not copy the entire response into the master database.
- Validate record shape and process well-formed records, rejecting malformed data and deduplicating so the master database contains only unique sightings. Retain eBird records with `obsValid: false` as `provisional`; do not present them as validated sightings.
- Exclude entire sightings marked `locationPrivate: true` from the internal model and DynamoDB, rather than retaining redacted sightings. Respect volunteer privacy; complete raw responses remain in the private S3 landing area for their configured retention period.
- Store the application fields needed for sightings, including at minimum bird/species, sighting timestamp, and sighting location. Keep the full raw payload in S3 rather than duplicating it unnecessarily in the master database.
- Expose read-only API endpoints for recent sightings, species lookup, region lookup, and health status. Support retrieval by region, species, and date.
- Allow region, species, and date filters to be combined. A sighting's region means the eBird source region used to poll it; retain this provenance independently of its identity.
- Have the health endpoint verify that the read function can access the master database, rather than reporting function liveness alone.
- Use `GET /sightings` with optional `region`, `species`, `date`, `limit`, and `cursor` query parameters. It returns the latest 10 sightings by default and at most 50 per request. Species lookup means filtering sightings by eBird species code; a separate species catalogue is not part of Phase 1.
- Interpret `date` as an ISO 8601 `YYYY-MM-DD` calendar day in `Europe/London`. Processed timestamps remain UTC. Future regional expansion may add explicitly versioned or opt-in regional date/time semantics; do not accept ambiguous US-style date input in Phase 1.
- A simple public homepage displays the 10 most recent sightings (species, location, timestamp) and the last successful end-to-end processing time by requesting the read API once when the page loads. It is served from a dedicated private S3 site bucket through CloudFront Origin Access Control; it does not poll in the background or cache API data.
- Treat transient upstream failures deliberately: retry network failures, eBird `429` responses, and `5xx` responses a bounded three times; route exhausted poller and processor deliveries to separate private dead-letter queues for investigation and manual replay.
- Use CloudWatch alarms for high-priority operational failures only: poller/processor errors, dead-letter queue messages, sustained API `5xx` errors, and no successful processing completion for 45 minutes. Send alarm notifications to an SNS topic; an administrator email subscription is optional and must be confirmed by its recipient. Do not notify on routine successful heartbeats.
- Terraform provisions AWS infrastructure.

## High-level data flow

EventBridge 15-minute heartbeat -> Poll Lambda -> eBird API (previous 24 hours) -> S3 raw response -> validation -> first-seen deduplication -> master database -> API Gateway -> read Lambda -> client/homepage.

The exact processor invocation mechanism and database access pattern are implementation decisions for their roadmap milestones.

## AWS and data

Use EventBridge, Lambda, S3, SQS, DynamoDB, API Gateway, CloudFront, IAM, CloudWatch, SNS, Parameter Store, and Terraform. DynamoDB is the intended master database and should be designed for application queries. Store one canonical item per sighting plus small, purpose-built query items with timestamp sort keys for latest, region, species, and region-plus-species lookups. The canonical item records `first_seen_at`, the raw-object ingestion time at which BirdAlert first encountered the sighting; query items remain sorted by `observed_at` for user-facing recency. These query items contain only the fields needed to answer their access pattern and must not duplicate the raw eBird payload.

The S3 lifecycle should expire old raw dumps. The current configured retention is one day, subject to deployment configuration.

## Phase 1 web application

The homepage is public and needs no user sessions, session cookies, authentication, or application state. Its plain static assets live in a dedicated `site/` directory and are deployed by Terraform to a separate private S3 site bucket. CloudFront is the only public origin and uses Origin Access Control to read that bucket, so it caches static assets without exposing direct S3 access. On page load, browser JavaScript makes one request to the API Gateway endpoint; the read Lambda queries the master database and returns the latest 10 sightings plus the timestamp of the last successfully completed processor invocation. Do not add background polling, a persistent cache, Redis, ElastiCache, or a heartbeat-written latest-sightings copy in Phase 1. Backend correctness must not depend on a cached homepage copy.

The read API primarily serves BirdAlert's own homepage using processed DynamoDB sightings, not the raw eBird dumps. Its unauthenticated public endpoint can also receive direct requests from other clients. Configure API Gateway with an initial steady rate of two requests per second and a burst limit of five requests for the sightings route, and one request per second with a burst limit of two for health. Keep these Terraform values configurable so they can be increased with observed demand. Bound each database request to at most 50 results and use query items rather than table scans to control cost; throttling is not a guaranteed spending cap.

## Security and quality

Use least-privilege IAM, Parameter Store for secrets/configuration, encryption where appropriate, input validation, and structured logging. Processing should be idempotent. Preserve raw API responses in S3 for their configured retention period and keep invalid records out of the master model.

Terraform creates each Lambda's log group before the function. Execution roles may create log streams and write events only inside their own group; log-group creation and retention management belong to Terraform.

## Phase 2 scope

Introduce authenticated users and personalised email alerts:

- Authenticate with Cognito; email address is the username.
- Users can maintain watchlists containing species and region, as specified in the original Phase 2 scope.
- User data includes email, registered location, and a user-updatable preferred alert radius expressed as “within X miles of me”.
- Compare newly processed sightings with each user's configured location and radius; a user can receive an email when a sighting is within that radius.
- Use SNS for email alerts as specified in the original architecture.

Location representation/storage, geolocation implementation, distance calculation, and Cognito schema are deliberately left to Phase 2 design. Do not specify them prematurely.

## Out of scope

Analytics, AI product features, mobile applications, advanced administration, social features, complex recommendations, multi-tenancy, and Phase 2 authentication/watchlists/alerts during Phase 1.

## Build roadmap

1. Terraform foundation.
2. Ingestion and 15-minute heartbeat.
3. Raw response retention, first-seen ingestion, validation, transformation, and deduplication.
4. Master database and read API.
5. Simple public homepage.
6. Phase 2: Cognito users and species/region watchlists.
7. Phase 2: personalised radius settings and alert matching.
8. Phase 2: SNS email alerts.
