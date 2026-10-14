# BirdAlert Bible

## Vision and purpose

BirdAlert is a real, single deployed web application for the UK. It ingests notable bird sightings from the eBird API, stores a reusable internal model, exposes sightings through an API and homepage, and later delivers personalised alerts.

The project demonstrates AWS, Terraform/IaC, DevOps practices, production-quality software engineering, and responsible use of modern AI development tools. It is one application, not a generic multi-tenant platform.

## Goals

Build a serverless-first, modular, observable, low-operational-cost application using AWS and Infrastructure as Code. Keep the design simple and extensible.

## Phase 1 scope

Implement the complete ingestion, read API, and simple homepage:

- A 15-minute heartbeat polls configured eBird regions. Deployment configuration supplies one or more valid eBird region codes; development may use `GB-ENG`. Do not assume or embed a definitive deployment region list.
- eBird provides the previous 24 hours of UK sightings. Each poll stores the complete raw response in one S3 bucket, under a region-based prefix.
- S3 is the raw landing area. The current lifecycle configuration retains raw data for one day; this remains a deployment/configuration choice, not an immutable architecture constraint.
- Processing extracts sightings relevant to the current 15-minute processing window from the 24-hour response. It must not copy the entire response into the master database.
- Validate and process records, reject invalid data, and deduplicate so the master database contains only unique sightings.
- Exclude entire sightings marked `locationPrivate: true` from the internal model and DynamoDB, rather than retaining redacted sightings. Respect volunteer privacy; complete raw responses remain in the private S3 landing area for their configured retention period.
- Store the application fields needed for sightings, including at minimum bird/species, sighting timestamp, and sighting location. Keep the full raw payload in S3 rather than duplicating it unnecessarily in the master database.
- Expose read-only API endpoints for recent sightings, species lookup, region lookup, and health status. Support retrieval by region, species, and date.
- Allow region, species, and date filters to be combined. A sighting's region means the eBird source region used to poll it; retain this provenance independently of its identity.
- Have the health endpoint verify that the read function can access the master database, rather than reporting function liveness alone.
- A simple public homepage displays the 10 most recent sightings (species, location, timestamp) by requesting the read API.
- Terraform provisions AWS infrastructure.

## High-level data flow

EventBridge 15-minute heartbeat -> Poll Lambda -> eBird API (previous 24 hours) -> S3 raw response -> extract current 15-minute slice -> validation, processing and deduplication -> master database -> API Gateway -> read Lambda -> client/homepage.

The exact processor invocation mechanism and database access pattern are implementation decisions for their roadmap milestones.

## AWS and data

Use EventBridge, Lambda, S3, DynamoDB, API Gateway, IAM, CloudWatch, Parameter Store, and Terraform. DynamoDB is the intended master database and should be designed for application queries. The exact key/index pattern for efficiently returning the latest 10 sightings is an implementation concern for the API milestone, not a product requirement to invent here.

The S3 lifecycle should expire old raw dumps. The current configured retention is one day, subject to deployment configuration.

## Phase 1 web application

The homepage is public and needs no user sessions, session cookies, authentication, or application state. On request, the API Gateway endpoint invokes a read Lambda, which queries the master database and returns the latest 10 sightings. Do not add a persistent cache solely for these results. A frontend refresh on a 15-minute cadence is optional; backend correctness must not depend on a cached homepage copy. Do not add Redis/ElastiCache or other caching infrastructure without a future measured need.

The read API primarily serves BirdAlert's own homepage using processed DynamoDB sightings, not the raw eBird dumps. Its unauthenticated public endpoint can also receive direct requests from other clients. Apply conservative configurable request/burst throttling and bounded database reads to reduce abuse and cost; throttling is not a guaranteed spending cap.

## Security and quality

Use least-privilege IAM, Parameter Store for secrets/configuration, encryption where appropriate, input validation, and structured logging. Processing should be idempotent. Preserve raw API responses in S3 for their configured retention period and keep invalid records out of the master model.

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
3. Raw response retention, current-window extraction, validation, transformation, and deduplication.
4. Master database and read API.
5. Simple public homepage.
6. Phase 2: Cognito users and species/region watchlists.
7. Phase 2: personalised radius settings and alert matching.
8. Phase 2: SNS email alerts.
