BirdAlert Bible v1.0
Architecture & Build Specification (Phases 1 and 2)
Contents
1. 1. Vision
2. 2. Goals
3. 3. Phase 1 Scope
4. 4. Functional Requirements
5. 5. High-Level Data Flow
6. 6. AWS Services
7. 7. Data Storage
8. 8. API Requirements
9. 9. Security
10. 10. Non-Functional Requirements
11. 11. Phase 2 Scope
12. 12. User Stories
13. 13. Out of Scope
14. 14. Build Roadmap
1. Vision
BirdAlert is an event-driven AWS platform that continuously ingests notable bird sightings from the
eBird API, stores them in a reusable internal data model, exposes them through an API, and later
delivers personalised alerts.
2. Goals
Build a production-style cloud platform using AWS services and Infrastructure as Code. Prioritise
clean architecture, modularity, observability, and incremental delivery.
3. Phase 1 Scope
Implement a complete ingestion pipeline:
- EventBridge scheduled poll every 15 minutes.
- Poll configured eBird regions.
- Store raw API payloads in a single S3 bucket using region-based prefixes.
- Validate payloads.
- Transform to an internal schema.
- Deduplicate observations.
- Store processed records in DynamoDB.
- Expose read-only API endpoints for search and retrieval.
Terraform provisions all infrastructure.
4. Functional Requirements
The system shall:
- Support one or more configured regions.
- Preserve every raw API response.
- Reject invalid payloads.
- Store only unique processed observations.
- Return sightings by region, species and date.
5. High-Level Data Flow
EventBridge -> Poll Lambda -> eBird API -> S3 (raw) -> Validation/Transform Lambda ->
DynamoDB -> API Gateway -> Client.
6. AWS Services
EventBridge, Lambda, S3, DynamoDB, API Gateway, IAM, CloudWatch, Parameter Store,
Terraform.
7. Data Storage
S3 is the immutable landing zone. DynamoDB stores the normalised application model optimised
for queries.
8. API Requirements
Provide endpoints for recent sightings, species lookup, region lookup and health status.
9. Security
Use IAM least privilege, Parameter Store for secrets/configuration, encrypted storage where
appropriate, input validation and structured logging.
10. Non-Functional Requirements
Serverless-first, idempotent processing, observable, modular, low operational cost and easily
extensible.
11. Phase 2 Scope
Introduce the first genuine user capability:
- User authentication (recommended: Cognito).
- Watchlists containing species and region.
- Notification engine that matches new observations against watchlists.
- SNS email alerts.
12. User Stories
As a user I can:
- Create an account.
- Maintain a watchlist.
- Receive an email when a matching notable sighting is ingested.
- Browse recent sightings via the API/UI.
13. Out of Scope
Analytics, AI, mobile applications, advanced administration, social features, and complex
recommendation systems.
14. Build Roadmap
Sprint 1: Terraform foundation.
Sprint 2: Ingestion pipeline.
Sprint 3: Validation and transformation.
Sprint 4: Read API.
Sprint 5: Basic frontend.
Sprint 6: Cognito.
Sprint 7: Watchlists.
Sprint 8: Alert engine.