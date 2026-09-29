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
- If an implementation decision is ambiguous or conflicts with the Bible, stop and ask the human rather than inventing a requirement.
- Prefer small, coherent, reviewable changes.
- Do not implement future roadmap items merely because they are described in the Bible.
- Do not add Phase 2 functionality while completing Phase 1 unless explicitly instructed.
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

1. Inspect the relevant existing implementation.
2. Identify the applicable requirement(s).
3. State the intended change and affected files.
4. Check for security and infrastructure implications.
5. Make the smallest change that satisfies the requirement.

After changing files:

1. Run relevant tests.
2. Run relevant formatting/linting/type/static checks where available.
3. Validate Terraform when Terraform changes are made.
4. Review the diff for accidental changes, secrets, and unrelated edits.
5. Report what changed, what was tested, and anything unresolved.

## AWS and Terraform

- Do not assume an AWS resource exists merely because Terraform defines it.
- Do not claim successful deployment or live AWS state without actually verifying it.
- Do not run destructive AWS or Terraform commands without explicit approval.
- Be especially careful with `terraform destroy`, state operations, resource replacement, and production resources.
- Keep environment-specific configuration explicit.
- Do not hard-code environment-specific values into application code when Terraform/configuration can supply them.

## Secrets

Never place API keys, passwords, tokens, credentials, or other secrets in source files.

Secret-bearing local files such as `*.auto.tfvars` are intentionally ignored by Git. Do not remove those ignore rules merely to make an agent workflow easier.

If a secret is discovered in source or tracked history:

- stop using it;
- tell the human it should be considered compromised;
- do not reproduce the secret in output;
- recommend rotation/remediation.

## Scope

Phase 1 is the current target:

EventBridge -> Poll Lambda -> eBird API -> S3 raw -> validation/transformation -> DynamoDB -> API Gateway -> client.

Phase 2 consists of authentication, watchlists, notification matching, and SNS email alerts.

Analytics, AI, mobile applications, advanced administration, social features, and complex recommendation systems are out of scope unless the human explicitly changes the project scope.

## Agent autonomy

The agent may inspect files, propose plans, implement approved work, run safe local tests, and report results.

The agent should not independently:

- redefine requirements;
- expand project scope;
- deploy to production;
- destroy infrastructure;
- rotate credentials;
- rewrite Git history;
- commit or push changes;
- introduce a new major framework or AWS service without explaining why it is required.

When a meaningful architectural choice is required, ask the human.

## Definition of done

A task is not complete merely because code was written.

A completed task should have:

- implementation matching the stated requirement;
- appropriate tests or verification;
- no newly introduced secrets;
- documentation updated where necessary;
- a clean review of the resulting diff;
- a concise report of changes, tests, and remaining issues.
