# BirdAlert Architecture

## Status

This document describes the intended Phase 1 architecture alongside the current implementation state. It is derived from `docs/BIBLE.md` and the repository as currently inspected.

## Intended Phase 1 architecture

BirdAlert is a serverless, event-driven AWS platform.

```text
EventBridge
    |
    v
Poll Lambda
    |
    v
eBird API
    |
    v
S3 raw landing zone
    |
    v
Validation / Transformation
    |
    v
DynamoDB
    |
    v
API Gateway
    |
    v
Client
```

The system should continuously ingest notable bird sightings, preserve raw API responses, validate and transform valid observations, deduplicate them, store the processed model in DynamoDB, and expose read-only API endpoints.

## AWS services

The Bible identifies:

- EventBridge
- Lambda
- S3
- DynamoDB
- API Gateway
- IAM
- CloudWatch
- Parameter Store
- Terraform

## Storage

S3 is the immutable raw landing zone for API responses.

DynamoDB stores the normalised application model and is optimised for application queries.

## Intended API

The read-only API should provide:

- recent sightings
- species lookup
- region lookup
- health status

Sightings should be retrievable by region, species, and date.

## Security and operational principles

The intended system is:

- least-privilege IAM
- Parameter Store for secrets/configuration
- encrypted storage where appropriate
- input validation
- structured logging
- idempotent processing
- observable
- modular
- low operational cost
- easily extensible

## Current implementation

The current active implementation is substantially earlier than the intended Phase 1 architecture.

Implemented:

- Poll Lambda
- eBird API request
- SSM Parameter Store lookup
- raw S3 storage
- Terraform modules for Lambda, IAM, SSM parameter, and S3
- Terraform bootstrap for remote state
- bucket versioning, encryption, and public-access blocking
- CloudWatch Logs IAM permissions

Not currently implemented in the active configuration:

- EventBridge schedule
- configurable region list
- validation
- transformation
- deduplication
- DynamoDB
- API Gateway
- API handlers
- tests

The repository contains placeholder/empty areas for API, transformer, validation, and tests.

## Known implementation mismatches

- The poller currently targets `GB-ENG` directly in application code.
- The poller currently writes under `ebird/` rather than region-based prefixes.
- The poller uses a hard-coded `/birdalert/dev/...` parameter path.
- The Terraform configuration supports environment-specific naming, creating a mismatch with the application hard-code.
- The root Terraform backend currently has a fixed `dev` state key despite dev and prod variable files existing.
- The README describes capabilities that are not yet implemented.

These are known gaps, not reasons to silently redesign the project.

## Architectural decision rule

When implementation details are not specified by the Bible, prefer the smallest design that satisfies the requirements and fits the existing serverless/Terraform architecture. If the choice materially changes the architecture, ask the human before proceeding.
