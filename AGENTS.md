# BirdAlert Agent Instructions

## Purpose

BirdAlert is a production-inspired, event-driven AWS platform for ingesting notable bird sightings from the eBird API, storing them in a reusable internal data model, exposing them through an API, and later delivering personalised alerts.

This file defines how an AI coding agent should work in this repository.

## Source of truth

Use these sources in this order:

1. `AGENTS.md` - rules for agent behaviour in the repository.
2. `docs/BIBLE.md` - authoritative product and architecture specification.
3. `docs/ARCHITECTURE.md` - current architecture and intended Phase 1 architecture.
4. `docs/REQUIREMENTS.md` - functional and non-functional requirements.
5. `docs/DEVELOPMENT.md` - development and verification workflow.
6. `docs/ROADMAP.md` - implementation sequence and current progress.
7. Existing source code and Terraform - the actual current implementation.

Do not assume the current code implements the Bible. The Bible describes the intended system; the repository describes the current state.

## Core rules

- Read the relevant documentation before making architectural or cross-cutting changes.
- Treat the Bible as the authoritative specification for product scope and intended architecture.
- Do not silently change architectural decisions or requirements.
- If a decision materially affects requirements, data contracts, security, infrastructure architecture, or externally visible behaviour, stop and ask the human.
- For routine, reversible, low-impact implementation choices that fit existing patterns, proceed without unnecessarily stopping for approval.
- Prefer small, coherent, reviewable changes.
- Do not implement future roadmap items merely because they are described in the Bible.
- Do not implement Phase 2 functionality while completing Phase 1 unless explicitly instructed.
- Preserve the serverless-first, modular, observable, low-operational-cost design.
- Terraform is the source of truth for AWS infrastructure.
- Keep IAM least-privilege.
- Keep secrets out of source code and committed configuration.
- Do not print, expose, commit, or reproduce credentials or secret values.
- Use Parameter Store for secrets/configuration as specified.
- Preserve raw eBird responses as required by the specification.
- Processing should be idempotent.
- Validate external API data before accepting it into the internal model.
- Add or update tests when behaviour changes.
- Run appropriate validation after changes.
- Update documentation when architecture, behaviour, interfaces, or operational procedures change.
- Do not create or modify Git commits unless explicitly asked.

## Change discipline

Before changing files:

1. Read the relevant documentation and implementation.
2. Identify the applicable requirement(s).
3. Determine the smallest coherent change.
4. Check for security and infrastructure implications.
5. State the intended change and affected files in the agent response.

The plan is normally an explanation of the intended work, not a request for approval. Proceed after stating the plan unless the change falls under the explicit approval boundaries below.

## Approval boundaries

The agent may proceed without additional approval for routine local development work and safe, reversible changes that satisfy an already-defined requirement.

The agent must ask the human before:

- changing product requirements;
- materially changing the architecture;
- changing an externally visible API or data contract when the required behaviour is not already defined;
- introducing a major new framework, AWS service, or dependency when the need is not already established;
- deploying to production;
- performing destructive AWS operations;
- running `terraform apply`;
- running `terraform destroy`;
- changing or rewriting Git history;
- committing or pushing Git changes;
- rotating, revoking, or replacing credentials.

## Terraform and AWS

- Do not assume an AWS resource exists merely because Terraform defines it.
- Do not claim successful deployment or live AWS state without actually verifying it.
- Read-only AWS inspection is permitted when necessary to answer a task, provided it does not mutate resources.
- `terraform plan` may be run for an explicitly authorised Terraform development task because it is a planning/read operation, but the agent must clearly report that it may contact the configured Terraform backend and AWS APIs.
- The agent must inspect the resulting plan and report any unexpected resource creation, destruction, replacement, or other significant change.
- `terraform apply`, `terraform destroy`, and other mutating infrastructure operations require explicit human approval.
- Be especially careful with state operations, resource replacement, and production resources.
- Keep environment-specific configuration explicit.
- Do not hard-code environment-specific values into application code when Terraform/configuration can supply them.

## Secrets and local files

Never place credentials, API keys, passwords, tokens, or other secrets in source files.

Secret-bearing local files such as `*.auto.tfvars` are intentionally ignored by Git. Do not remove those ignore rules merely to make an agent workflow easier.

Ignored or untracked files are still sensitive. The agent must:

- never reproduce secret values in responses;
- never copy secrets into source code, documentation, tests, logs, generated files, or commits;
- avoid unnecessarily reading secret-bearing files;
- if a secret is discovered, report only that a secret was found, without displaying its value.

If a secret is discovered in source code or tracked Git history:

- stop using it;
- tell the human it should be considered compromised;
- do not reproduce the secret;
- recommend rotation/remediation.

If a credential is discovered only in an ignored or untracked local file, do not treat that fact alone as evidence that it was committed or publicly exposed. Still avoid reproducing it and recommend removing stale credentials and rotating any credential that has otherwise been exposed.

## Scope

Phase 1 is the current target:

EventBridge -> Poll Lambda -> eBird API -> S3 raw -> validation/transformation -> DynamoDB -> API Gateway -> client.

Phase 2 consists of authentication, watchlists, notification matching, and SNS email alerts.

Analytics, AI, mobile applications, advanced administration, social features, and complex recommendation systems are out of scope unless the human explicitly changes the project scope.

## Agent autonomy

The agent may:

- inspect repository files;
- inspect safe local configuration;
- propose implementation plans;
- implement approved requirements;
- make routine reversible implementation choices;
- run safe local tests and validation;
- run read-only AWS inspection when useful;
- run `terraform plan` for an explicitly authorised Terraform development task;
- review its own changes;
- report results.

The agent should not independently:

- redefine requirements;
- expand project scope;
- deploy to production;
- apply or destroy Terraform infrastructure;
- rewrite Git history;
- rotate credentials;
- commit or push changes;
- introduce major architecture changes without human involvement.

When a meaningful architectural choice is required, ask the human.

## Definition of done

A task is not complete merely because code was written.

A completed task should have:

- implementation matching the stated requirement;
- appropriate tests or verification;
- no newly introduced secrets;
- documentation updated where necessary;
- a clean review of the diff;
- a concise report of:
  - files changed;
  - what changed;
  - tests/checks run;
  - infrastructure changes planned, if applicable;
  - anything unresolved.