# BirdAlert 𓅪
A UK-first AWS portfolio application that ingests notable eBird sightings and displays public reports on a minimal website. Terraform provisions the infrastructure. Phase 1 demonstrates ingestion, validation, storage, a read API, static hosting, and operational failure handling; personalised user alerts belong to Phase 2.

Phase 1 is implemented in the repository. Deployment of the latest corrections and recorded live failure-path checks remain prerequisites for completion; local tests alone do not establish successful AWS operation. See the [roadmap](docs/ROADMAP.md) for current status.

## How it works

```text
EventBridge (every 15 minutes) -> Poll Lambda -> eBird (back=1)
    -> private raw S3 -> Processor Lambda -> DynamoDB
    -> API Gateway / Read Lambda -> browser

CloudFront -> separate private S3 site bucket -> browser
Failures -> separate poller/processor SQS queues
CloudWatch problem alarms -> SNS -> optional administrator email
```

## Decisions worth defending

- The 15-minute schedule is a polling heartbeat. First-seen ingestion captures late-submitted observations without repeatedly storing overlapping snapshots. Conditional transactions protect canonical identity; batch reads avoid repeat writes.
- Private-location sightings are excluded from processed storage. Provisional sightings are retained and labelled honestly. Complete upstream responses stay in access-restricted raw S3 for the configured lifecycle period, currently one day.
- DynamoDB uses on-demand billing and small indexed query records for bounded reads, avoiding table scans and a separate cache. Public API throttles reduce abuse but do not guarantee a spending cap.
- The homepage fetches once on page load. CloudFront caches static assets from a separate private bucket through Origin Access Control; live sightings come through the API.
- UK calendar-day queries use `Europe/London`, including daylight-saving changes. Stored timestamps use UTC. The displayed processing time is separate from when a bird was observed.
- Transient eBird requests have three bounded retries. Poller and processor failures are retained separately for investigation and manual replay. Only operational problems raise notifications; successful heartbeats do not generate email.
- Terraform owns log-group creation and 30-day retention. Each function can write only to its own log streams. Configuration and secret lookup use Parameter Store, and environment-specific values stay outside application code.

The project demonstrates AWS and Terraform design decisions alongside an agent-assisted development workflow. [Design decisions](docs/DECISIONS.md) preserves the reasoning and trade-offs; it is the detailed reference for portfolio and interview preparation.

## Development and operation

- [Bible](docs/BIBLE.md): authoritative product scope and architecture.
- [Architecture](docs/ARCHITECTURE.md): implementation, data access patterns, and known limitations.
- [Requirements](docs/REQUIREMENTS.md): expected behaviour and security boundaries.
- [Development guide](docs/DEVELOPMENT.md): package builds, validation, deployment, recovery, and live acceptance.
- [Roadmap](docs/ROADMAP.md): progress and Phase 2 boundary.

Application code lives in `src/`, static assets in `site/`, infrastructure in `terraform/`, and local Python tests in `tests/`. Terraform tests use mocked providers. Keep API keys, local variable files, and Terraform state out of source control.

The current backend state key is fixed to dev. A production environment needs a separately reviewed backend configuration; changing the variable file alone does not isolate state. Phase 2 authentication, watchlists, and personalised notifications are not implemented.
