# BirdAlert design decisions

This record preserves agreed choices and their rationale for project review. `BIBLE.md` remains the authoritative specification; `ROADMAP.md` distinguishes implementation from future work. Git history preserves changes to these documents.

## 2026-10-14 - Private sightings excluded entirely

Accepted and implemented locally. A record marked `locationPrivate: true` is excluded before transformation into the internal model and is blocked again at the DynamoDB write boundary. Missing or non-boolean privacy flags also fail validation. Rejection reporting uses counts and generic reasons, not private sighting details.

Rationale: BirdAlert uses volunteer contributions and must respect their privacy choices even when an upstream endpoint returns the record. Keeping a redacted sighting still retains information about that contribution, so entire-record exclusion replaces the earlier redaction-only policy.

Complete raw responses remain in the access-restricted S3 landing bucket for their configured retention, as required by the Bible. They are not exposed by the read API. This change prevents new private records entering DynamoDB; any previously persisted private records would require separately reviewed cleanup. No AWS cleanup is performed by this change.

## 2026-10-14 - Provisional eBird sightings retained with explicit status

Accepted and implemented locally. Well-formed eBird records with `obsValid: false` enter the internal model and DynamoDB with `validation_status: "provisional"`; records with `obsValid: true` are marked `"validated"`. The read API returns this status so clients do not mistake a provisional report for a validated one. `obsValid` must still be a boolean, and malformed records remain rejected.

Rationale: the UK notable-feed test run contained predominantly provisional records. Excluding them made the MVP unable to demonstrate its end-to-end ingestion, storage, and API flow. The project deliberately prioritises demonstrating a responsible AWS and agentic-development workflow while preserving an honest data-quality signal for the client and future refinements. This is not a claim that provisional sightings have been confirmed.

Private-location exclusion remains unchanged: `locationPrivate: true` records are never persisted or exposed. The change is intentionally limited to eBird's validation marker, not contributor privacy.

The processor now accepts eBird timestamps with minute or second precision. Date-only timestamps remain rejected in Phase 1 because they cannot be sorted or presented with a truthful observation time; their treatment is deferred for later design.

## 2026-10-14 - First-seen ingestion from overlapping eBird snapshots

Accepted and implemented locally. EventBridge continues to invoke the poller every 15 minutes and eBird continues to return the preceding 24 hours. The processor validates every snapshot but persists a well-formed non-private sighting only when its canonical identity has not previously been recorded by BirdAlert. The canonical DynamoDB item records the raw-object ingestion time as `first_seen_at`; public query records continue to sort by the actual `observed_at` timestamp.

Before writing, the processor uses DynamoDB `BatchGetItem` to identify canonical sightings already present, then conditionally transaction-writes only new canonical and query records. The conditional write remains the concurrency safeguard. If an already-known sighting arrives through a new eBird source region, the processor updates its provenance and the two region-specific query records without rewriting the global latest or species records.

Rationale: eBird reports can be submitted long after their observation time, so filtering the 24-hour response to the last 15 minutes excluded most public sightings and made the application appear stale. First-seen ingestion captures those reports while preserving the EventBridge heartbeat, Lambda and S3 event-driven flow that demonstrates the intended AWS architecture. Batch identity reads keep overlapping snapshots from causing repeated transactional writes, reducing DynamoDB cost without adding a cache, service, or operational burden. `first_seen_at` preserves an operational audit trail while `observed_at` remains the truthful user-facing ordering.

Privacy is unchanged: `locationPrivate: true` records remain excluded before any internal persistence, and date-only timestamps remain outside Phase 1 until their product treatment is explicitly designed.

The processor Lambda timeout is set to 180 seconds. This protects the first execution, when a full 24-hour snapshot can legitimately introduce many canonical sightings, while preserving pay-for-use Lambda billing; it does not reserve capacity or make normal quick invocations cost more.

## 2026-10-14 - Region means eBird poll source region

Accepted and implemented locally. API region filters refer to the eBird region code used to poll sightings, such as the configured development code `GB-ENG`. A sighting can retain multiple source regions when overlapping polls return it. Region does not participate in sighting identity and is unrelated to the AWS deployment region.

Rationale: using the source's region vocabulary keeps ingestion and retrieval consistent and preserves room for future expansion. The MVP remains UK-only; future international coverage would need additional design, including observation timezone handling.

## 2026-10-14 - App-focused public API with combined filters

Accepted and implemented locally. The read API primarily serves BirdAlert's homepage using processed sightings accumulated in DynamoDB. It does not serve raw eBird dumps or poll eBird on each client request. The upstream 24-hour response window and raw S3 retention do not impose a 24-hour retention limit on processed DynamoDB sightings; the table currently has no expiry.

Region, species, and date filters may be combined. `GET /sightings` accepts optional `region`, `species`, `date`, `limit`, and `cursor` parameters. It returns 10 latest sightings by default and permits at most 50 records in one page. Species lookup means filtering sightings by eBird species code; a separate species catalogue is not part of Phase 1. Public unauthenticated access also allows direct requests from other clients, so app ownership cannot be enforced simply by hiding the endpoint or restricting browser CORS origins.

Rationale: combined filters support useful app queries while a 50-result maximum bounds DynamoDB work and response size. API Gateway starts at two requests per second with a burst of five for sightings, and one request per second with a burst of two for health. These Terraform-managed values can increase with observed demand. API Gateway throttles are best-effort targets, not guaranteed request ceilings or spending caps. No new protection service is selected here.

## 2026-10-14 - Static homepage delivery and page-load-only data reads

Accepted and implemented locally. Plain static homepage assets live in the repository's `site/` directory. Terraform deploys them to a dedicated private S3 site bucket, and CloudFront delivers them publicly using Origin Access Control. The raw-data bucket remains separate and inaccessible to CloudFront.

The homepage will request `GET /sightings` once when a user opens the page. It will not poll in the background, and CloudFront will cache only static site assets rather than proxying or caching the API response. API Gateway, the read Lambda, and the bounded DynamoDB latest-sightings query remain the live data path. Terraform will configure the API CORS origin for the CloudFront site domain.

Rationale: expected users will normally view the page briefly, so a scheduled client-side refresh would add requests without meaningful benefit. A single page-load request gives each visitor current data while keeping Lambda and DynamoDB interactions low. The existing bounded query and API throttles provide the appropriate low-cost protection at this stage. CloudFront reduces direct S3 asset reads and protects the site bucket without adding a second copy of dynamic sighting data or cache invalidation complexity. `PriceClass_100` serves the UK while limiting edge-location cost, and the five-minute asset cache balances reduced S3 reads with timely Terraform-deployed updates.

## 2026-10-14 - End-to-end data freshness indicator

Accepted and implemented locally. After a processor invocation successfully handles a raw S3 object, it overwrites one fixed-key DynamoDB operational-status item with `last_successful_processing_at`. `GET /sightings` returns this nullable timestamp alongside its bounded sighting result, and the homepage formats it in `Europe/London`. The timestamp is initially absent until the first successful processing run after deployment.

Rationale: a poll start or successful eBird response does not prove that new data has passed validation, persistence, and the read path. Recording processor completion provides an honest, low-cost end-to-end freshness signal for visitors. A single status item adds one small DynamoDB write per successful raw object and one lightweight read per API request; it does not create a cache or duplicate sightings. It needs no table schema change because DynamoDB is schemaless, and the existing least-privilege processor and read permissions already allow `PutItem` and `GetItem` on this table.

## 2026-10-15 - Operational failure handling and high-priority alerting

Accepted and implemented locally. The poller retries only transient upstream network, `429`, and `5xx` failures three times using bounded exponential backoff. Invalid payloads and non-transient client errors fail visibly without retry. Exhausted poller and processor deliveries are retained in separate encrypted SQS dead-letter queues for 14 days, with manual replay in Phase 1.

CloudWatch logs retain 30 days. High-priority CloudWatch alarms cover poller/processor errors, non-empty dead-letter queues, sustained API `5xx` errors, and no processor completion for 45 minutes. Alarm actions publish to an SNS operational topic. An administrator email subscription is optional Terraform configuration and requires AWS's out-of-band recipient confirmation. Routine successful 15-minute heartbeats do not notify.

Rationale: separate queues distinguish upstream-polling failures from raw-object processing failures, making diagnosis and safe replay clearer. Three retries balance recovery from brief eBird or network disruption against unnecessary repeat requests and cost. Retaining failed events makes failure observable without exposing their content through logs. Problem-only alerts provide useful operational signal without creating routine inbox noise; optional email keeps the deployment portable and avoids embedding administrator contact details in source control.

Completion correction: an EventBridge DLQ captures failure to deliver an event to Lambda; it cannot capture an error raised after Lambda accepts that event. The poller therefore also has a Lambda asynchronous failure destination pointing to the same poller DLQ, with queue-scoped `sqs:SendMessage` permission. Both poller and processor asynchronous configurations permit two execution retries with a one-hour event age, independently of the three eBird request retries. The poller timeout now allows five minutes per configured region, capped at fifteen minutes, instead of the shared 30-second default. This gives the current deployment room to complete requests and backoff; it does not reserve capacity or increase billing for normal quick invocations. Revisit the budget before expanding to larger region sets.

## 2026-10-14 - UK calendar-date API filter

Accepted and implemented locally. The `date` query parameter is ISO 8601 `YYYY-MM-DD` and selects a calendar day in `Europe/London`. DynamoDB retains timestamps in UTC, and the read Lambda converts the start and end of the requested UK day to UTC before querying.

Rationale: BirdAlert is UK-first, so human-facing date queries should align with UK calendar days, including daylight-saving transitions. ISO `YYYY-MM-DD` is intentionally unambiguous across locales. Any future support for regional date/time semantics must be explicit, versioned or opt-in, and designed alongside international expansion; Phase 1 does not accept ambiguous US-style date inputs.

## 2026-10-14 - Canonical sightings and DynamoDB query records

Accepted and implemented locally. DynamoDB retains one canonical record per unique sighting. Small query records with timestamp sort keys support the latest, region, species, and region-plus-species access patterns. They contain only fields required to answer the corresponding read request and never copy a raw eBird payload. A single `query-by-key` global secondary index uses query keys `LATEST`, `REGION#{region}`, `SPECIES#{species}`, and `REGION#{region}#SPECIES#{species}`; its timestamp-prefixed sort key makes reverse-order DynamoDB queries efficient. The processor batch-checks canonical identities, conditionally creates the canonical record with its four query records only when first seen, and skips a repeat from an existing source region. A duplicate from a new source region updates provenance and only that region's two query records.

Rationale: the canonical record is the authoritative stored sighting. Purpose-built query records make the public API's bounded reads predictable and avoid costly table scans or a separate cache. The exact key shape, transactional write strategy, cursor encoding, and response projection remain Milestone 5 implementation details.

## 2026-10-14 - Health verifies database access

Accepted and implemented locally. The health endpoint verifies that the read function can reach and read from the master DynamoDB table using its normal credentials and permissions.

Rationale: function liveness alone can report success while the application's database access is broken, which is misleading during troubleshooting. The check reports database accessibility; ingestion freshness is a separate concern. It returns `200` with database reachability after a successful lightweight `GetItem`, and `503` when that read fails.

## 2026-10-14 - Raw bucket naming suffix

Accepted and implemented locally. The raw bucket name now includes a stable Terraform-generated eight-character hexadecimal suffix. The suffix is created once and retained in Terraform state, so dependent configuration receives a consistent bucket name.

Rationale: S3 bucket names occupy a global namespace. The suffix substantially reduces naming-collision risk while retaining meaningful project and environment components. It does not guarantee availability.

The raw bucket module's outputs supply its resulting name and ARN to the poller, processor, IAM policies, and S3 notification resources. The established Terraform state bucket retains its existing six-character suffix because changing the backend bucket would require replacement and state migration. Applying this raw-bucket change to an existing environment will replace that bucket; review the Terraform plan before applying.
