# BirdAlert Roadmap

## Current target

Complete Phase 1.

The Bible's roadmap is:

1. Terraform foundation
2. Ingestion pipeline
3. Validation and transformation
4. Read API
5. Basic frontend
6. Cognito
7. Watchlists
8. Alert engine

The Bible's explicit Phase 1 scope is the ingestion and read API pipeline. The frontend appears in the roadmap as Sprint 5, so its status as a Phase 1 completion criterion should be confirmed before implementation.

## Current repository state

Completed or substantially implemented:

- Terraform foundation
- poller Lambda
- eBird API integration
- SSM Parameter Store integration
- raw S3 storage
- supporting IAM
- Terraform remote-state bootstrap

Not yet implemented:

- EventBridge 15-minute schedule
- configurable multi-region polling
- region-based raw storage keys
- validation
- transformation
- deduplication
- idempotent processing
- DynamoDB processed storage
- read-only API
- API Gateway
- structured logging
- explicit retry/failure handling
- tests
- basic frontend

## Proposed implementation sequence

These milestones are an implementation sequence derived from the current gap analysis:

### Milestone 1 - Configuration-driven polling

- configure one or more regions;
- remove environment-specific parameter paths from application code;
- use region-based raw S3 prefixes;
- use collision-resistant object keys;
- preserve every response.

### Milestone 2 - EventBridge scheduling

- add a 15-minute EventBridge schedule;
- connect it to the poller;
- add Lambda invocation permission;
- verify the schedule safely.

### Milestone 3 - Validation and internal model

- define the required internal record shape;
- validate incoming eBird records;
- reject invalid records;
- add focused tests.

### Milestone 4 - Transformation and deduplication

- transform valid eBird observations;
- define the uniqueness/idempotency mechanism;
- ensure repeated processing does not create duplicate processed observations;
- add tests.

### Milestone 5 - DynamoDB

- define the DynamoDB table and query model;
- store processed observations;
- provide least-privilege write access;
- test the persistence path.

### Milestone 6 - Read API

- implement API Gateway;
- add recent sightings;
- add species lookup;
- add region lookup;
- add health status;
- design DynamoDB indexes around the actual query requirements.

### Milestone 7 - Operational hardening

- structured logging;
- deliberate failure/retry behaviour;
- broader integration verification;
- environment/deployment review.

### Milestone 8 - Frontend decision

Confirm whether the Bible's Sprint 5 basic frontend is required for the Phase 1 completion target before implementing it.

## Phase 2

After Phase 1:

- Cognito authentication
- watchlists
- notification matching
- SNS email alerts

Do not implement Phase 2 merely because these items are documented.
