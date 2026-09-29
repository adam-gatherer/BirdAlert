# BirdAlert Development Guide

## Development model

BirdAlert is being developed incrementally against the roadmap in `docs/ROADMAP.md`.

The AI agent is an implementation assistant, not the owner of the architecture. Human approval is expected for material architectural decisions.

BirdAlert is one public UK application, not a generic multi-tenant platform. Keep deployment-specific values separate from configuration mechanisms: code and Terraform define how values are supplied; the deployer supplies actual deployment values. Do not invent a definitive eBird region list or add API documentation to this repository. Development may use the existing `GB-ENG` region.

## Standard agent workflow

For each task:

1. Read `AGENTS.md`.
2. Read the relevant sections of `docs/BIBLE.md`.
3. Read the relevant project documentation.
4. Inspect the current implementation.
5. Identify the smallest coherent change.
6. Explain the intended change before making it when the task is non-trivial.
7. Implement the change.
8. Run relevant tests and validation.
9. Review the diff.
10. Update documentation if behaviour or architecture changed.
11. Report:
   - files changed;
   - what changed;
   - tests/checks run;
   - any unresolved issues.

## Terraform changes

For Terraform work, use the normal Terraform validation workflow appropriate to the affected directory.

For an explicitly authorised Terraform development task, review:

- formatting;
- configuration validity;
- planned resource changes.

`terraform plan` may contact the configured backend and AWS APIs. Follow `AGENTS.md` for when it is appropriate and report this side effect and any unexpected resource changes. Do not apply infrastructure without the required explicit approval.

Do not apply destructive or production changes without explicit human approval.

Do not claim that AWS deployment succeeded unless it has actually been performed and verified.

## Python changes

For Python changes:

- keep dependencies explicit;
- preserve the Lambda entry point where applicable;
- handle external API failures deliberately;
- avoid hard-coded environment-specific configuration;
- add focused tests for new behaviour where practical.

## Secrets

Never commit credentials.

The repository intentionally ignores secret-bearing Terraform variable files. Local secret values should remain local.

Do not echo secrets into logs, test output, generated documentation, or agent reports.

## Git

The human controls commits and pushes unless explicitly requesting the agent to perform them.

Before handing work back:

- inspect `git diff`;
- inspect `git status`;
- check for accidentally created files;
- check for secrets;
- ensure unrelated changes were not introduced.

## AWS verification

Repository configuration and live AWS state are different things.

If a task requires knowledge of live AWS state, explicitly perform a safe read-only check or tell the human that the state has not been verified.

## Documentation

Update documentation when:

- an architectural decision changes;
- a requirement is clarified;
- an API contract changes;
- infrastructure changes materially;
- a new development procedure is introduced.

Keep documentation concise and useful to both humans and coding agents.
