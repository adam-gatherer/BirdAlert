# BirdAlert Requirements

## Source

Requirements are derived from `docs/BIBLE.md` and the current repository assessment.

## Phase 1 functional requirements

The system shall:

1. Support one or more configured eBird regions.
2. Poll eBird on a 15-minute schedule.
3. Preserve every raw API response in S3.
4. Store raw responses using region-based prefixes.
5. Validate external API payloads.
6. Reject invalid payloads.
7. Transform valid observations into an internal schema.
8. Store only unique processed observations.
9. Make processing idempotent.
10. Store processed observations in DynamoDB.
11. Provide read-only API access.
12. Return sightings by region, species, and date.
13. Provide recent sightings access.
14. Provide species lookup.
15. Provide region lookup.
16. Provide a health endpoint.

## Security requirements

The system shall:

- use least-privilege IAM;
- use Parameter Store for secrets/configuration;
- encrypt storage where appropriate;
- validate external input;
- avoid credentials in source code.

## Non-functional requirements

The system should be:

- serverless-first;
- idempotent;
- observable;
- modular;
- low operational cost;
- easily extensible.

## Phase 2 requirements

Phase 2 introduces:

- user authentication, recommended as Cognito;
- watchlists containing species and region;
- notification matching against new observations;
- SNS email alerts.

## Out of scope

The Bible explicitly places these out of scope:

- analytics;
- AI;
- mobile applications;
- advanced administration;
- social features;
- complex recommendation systems.

## Current verification status

The repository assessment indicates that tests are currently absent and the following Phase 1 capabilities are not yet implemented:

- EventBridge scheduling
- configurable regions
- validation
- transformation
- deduplication/idempotency
- DynamoDB
- read API
- structured logging/retry behaviour

These are implementation-status observations, not changes to the requirements.
