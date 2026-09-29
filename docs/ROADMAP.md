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

These milestones are an implementation sequence derived from the current gap analysis.

---

## Milestone 1 - Configuration-driven polling

### Objective

Remove the current poller's hard-coded environment and region assumptions so that the ingestion Lambda can safely poll one or more configured eBird regions while preserving every successful raw API response.

### Configuration decisions

For Milestone 1:

- The list of eBird regions should be supplied through Terraform/application configuration rather than hard-coded in Python.
- The environment-specific SSM parameter path should be supplied through configuration rather than hard-coded in Python.
- Terraform should remain responsible for environment-specific values.
- The Lambda should receive its runtime configuration through environment variables unless an existing project pattern provides a clearly better mechanism.
- The initial development environment remains `dev`.
- Existing production infrastructure should not be modified or deployed as part of this milestone.

The exact configuration variable names may be chosen by the implementer if they are clear, consistent, and documented.

### Region handling

The poller should:

- accept one or more configured eBird region identifiers;
- make one eBird request per configured region;
- associate each response with the region that produced it;
- avoid hard-coding `GB-ENG` in application code.

For the current development configuration, preserve the existing `GB-ENG` behaviour by configuring it as the initial region.

The region identifier used by eBird should also be used consistently as the region component of the S3 key unless an implementation constraint requires another documented mapping.

### SSM parameter handling

The poller should not contain: `/birdalert/dev/...` or any other environment-specific parameter path.

Terraform should provide the appropriate parameter name/path for the environment.

The application should read the configured parameter name at runtime and continue to use `WithDecryption=True`.

### S3 raw object layout

Raw responses should use a region-based prefix.

The target layout is conceptually: `<region>/<timestamp-or-unique-id>.json`


For example: `GB-ENG/20260929T103000Z-<unique-id>.json`


The exact unique suffix may be chosen by the implementer.

The object-key scheme must ensure that two successful writes cannot overwrite each other merely because they occur within the same second.

The key should contain enough information to identify the source region and the ingestion event.

### Raw response preservation

For every successful eBird API response:

* attempt to write the complete raw JSON response to S3;
* do not silently discard successful responses;
* do not overwrite a previous raw response because of key collision;
* report S3 write failures as failures rather than claiming successful ingestion.

HTTP error responses are not successful raw observations and do not need to be stored as successful ingestion records for this milestone.

If the API returns a successful HTTP response that cannot be parsed as JSON, the Lambda must fail rather than silently treating the response as valid JSON.

Validation of individual observation records belongs to a later milestone.

### Error behaviour

For Milestone 1:

* HTTP errors from eBird should cause the relevant polling operation to fail visibly.
* Request timeouts and connection failures should fail visibly.
* Invalid JSON from a successful response should fail visibly.
* S3 write failures should fail visibly.
* Do not introduce a complex retry framework unless required by the existing Lambda/AWS behaviour or explicitly requested.
* Do not add validation/transformation/deduplication logic yet; those belong to later milestones.

For multiple configured regions, a failure in one region must not silently be reported as though all configured regions succeeded.

The implementation should make the success/failure status of each region clear in its result/logging.

### Testing and acceptance criteria

Milestone 1 is complete when:

* [ ] `GB-ENG` is no longer hard-coded as the only polling region.
* [ ] The region list is supplied through configuration.
* [ ] The SSM parameter path is supplied through configuration.
* [ ] The existing dev configuration continues to poll `GB-ENG`.
* [ ] Multiple configured regions result in separate eBird requests.
* [ ] Raw objects use region-based S3 prefixes.
* [ ] Two writes in the same second cannot overwrite one another because of the object-key design.
* [ ] Successful raw API responses are stored completely.
* [ ] HTTP failures are surfaced as failures.
* [ ] request/network failures are surfaced as failures.
* [ ] invalid JSON is surfaced as a failure.
* [ ] S3 write failures are surfaced as failures.
* [ ] No credentials or API keys are added to source code.
* [ ] Focused tests cover the new configuration and key-generation behaviour.
* [ ] Terraform configuration is formatted and validated.
* [ ] The resulting diff contains no unrelated changes.
* [ ] Documentation reflects the final configuration interface.

### Explicitly out of scope

Do not implement the following as part of Milestone 1:

* EventBridge scheduling
* validation of individual bird records
* transformation to the internal schema
* deduplication
* DynamoDB
* API Gateway
* frontend
* Cognito
* watchlists
* SNS alerts
* complex retry systems
* production deployment

---

## Milestone 2 - EventBridge scheduling

* add a 15-minute EventBridge schedule;
* connect it to the poller;
* add Lambda invocation permission;
* verify the schedule safely.

## Milestone 3 - Validation and internal model

* define the required internal record shape;
* validate incoming eBird records;
* reject invalid records;
* add focused tests.

## Milestone 4 - Transformation and deduplication

* transform valid eBird observations;
* define the uniqueness/idempotency mechanism;
* ensure repeated processing does not create duplicate processed observations;
* add tests.

## Milestone 5 - DynamoDB

* define the DynamoDB table and query model;
* store processed observations;
* provide least-privilege write access;
* test the persistence path.

## Milestone 6 - Read API

* implement API Gateway;
* add recent sightings;
* add species lookup;
* add region lookup;
* add health status;
* design DynamoDB indexes around the actual query requirements.

## Milestone 7 - Operational hardening

* structured logging;
* deliberate failure/retry behaviour;
* broader integration verification;
* environment/deployment review.

## Milestone 8 - Frontend decision

Confirm whether the Bible's Sprint 5 basic frontend is required for the Phase 1 completion target before implementing it.

## Phase 2

After Phase 1:

* Cognito authentication
* watchlists
* notification matching
* SNS email alerts

Do not implement Phase 2 merely because these items are documented.