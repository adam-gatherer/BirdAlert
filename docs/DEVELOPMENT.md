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

## Production deployment

Production uses the `account-b` AWS CLI profile, a state bucket in that account, and the `birdalert.gatherer.tech` Route 53 hosted zone. The root configuration deliberately uses a partial S3 backend: select its state location during `init`, rather than editing tracked Terraform files. The production backend is `terraform/backend/prod.hcl`; its state key is separate from dev.

Before planning, ensure the production eBird API key is supplied through an ignored local `*.auto.tfvars` file or normal Terraform variable input. Never put it in `prod.tfvars`, a backend file, a command history, or documentation.

From the repository root in PowerShell:

```powershell
$env:AWS_PROFILE = "account-b"
python build_lambdas.py
terraform -chdir=terraform/root init -reconfigure -backend-config="../backend/prod.hcl"
terraform -chdir=terraform/root plan -var-file="../environments/prod.tfvars" -var-file="../environments/secrets.auto.tfvars"
```

If the S3 backend reports that it cannot find credentials despite a successful `aws login --profile account-b`, export the profile credentials into the current PowerShell process without printing them, then repeat the Terraform command:

```powershell
$credentialLines = aws configure export-credentials --profile account-b --format env-no-export
foreach ($credentialLine in $credentialLines) {
  if ($credentialLine -match "^([^=]+)=(.*)$") {
    Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
  }
}
```

Review the plan before applying. A first production plan creates the independent application stack, an ACM certificate in `us-east-1`, DNS-validation records, a CloudFront alternate domain, and Route 53 A/AAAA aliases for `birdalert.gatherer.tech`. ACM validation and CloudFront distribution deployment can take several minutes. Apply only with explicit approval, then verify the homepage, `/health`, sightings API, and processing freshness through the production domain.

For dev, initialise with `-backend-config="../backend/dev.hcl"`; do not initialise dev with the production backend configuration or vice versa.

When Terraform begins managing a Lambda log group that was created by an earlier deployment, import that existing log group into Terraform state before `apply`; do not delete it merely to set retention. Use the stable Terraform resource address and the `/aws/lambda/<function-name>` log-group name for the active environment.

The root configuration creates log groups before their Lambda functions to prevent automatic log-group creation from racing Terraform on a fresh deployment. Existing untracked groups still require import. After a partial apply, only import groups Terraform still plans to create; already tracked groups need no further import.

For the existing dev read log group, run these commands from `terraform/root` in Windows PowerShell. `--%` preserves the quoted resource key for Terraform, and the variable file supplies the deployment configuration:

```powershell
terraform --% import -var-file="../environments/dev.tfvars" aws_cloudwatch_log_group.lambda[\"read\"] "/aws/lambda/birdalert-dev-read"
terraform plan -var-file="../environments/dev.tfvars"
```

The import must report success. Review the plan before applying; the imported log group should no longer be listed for creation. If an old saved plan was used, discard it and create a fresh plan after import.

Do not claim that AWS deployment succeeded unless it has actually been performed and verified.

For the Milestone 7 poller retry-budget and failure-destination correction, review a new dev plan and apply it through the usual workflow. It should update the poller timeout and add its queue-scoped IAM policy/attachment and Lambda asynchronous invocation configuration; it should reuse the existing poller DLQ. No Lambda package rebuild is needed for this Terraform-only correction. Live failure-destination delivery and alarm behaviour still require verification after deployment. An EventBridge delivery failure and a Lambda execution failure use different message envelopes; inspect the envelope and replay its original event manually after resolving the cause.

Run `terraform -chdir=terraform/root test` from the repository root to check poller failure-destination wiring and timeout budgets using mocked providers and isolated test state. These tests do not contact AWS or deploy resources. They still require the providers and existing Lambda package files to be available locally.

## Deploying the completion-review corrections

The read Lambda date-filter correction and the poller `back=1` correction change application code, so rebuild their deployment packages before Terraform planning. From the repository root, with the project's Python environment active:

```powershell
python scripts/build_poller.py
python scripts/build_read.py
terraform -chdir=terraform/root init
terraform -chdir=terraform/root plan -var-file="../environments/dev.tfvars"
```

Review the plan, then run the usual human-approved apply. The expected changes are poller/read package hashes and the three scoped logging policies; any outstanding earlier corrections may also appear. No replacement of the sighting table, raw bucket, site bucket, or CloudFront distribution is needed for these corrections. Keep the processor package available locally even if it does not need rebuilding. Use the existing ignored secret configuration or normal variable input; never copy secrets into these commands or tracked files.

Run local checks from the repository root:

```powershell
python -m unittest discover -s tests
terraform -chdir=terraform/root test
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform/root validate
```

Run `terraform init` again if Terraform reports uninstalled local test modules. The logging-policy tests inspect the configured actions and resource scope; mocked providers do not prove live IAM authorisation or notification delivery.

## Phase 1 live acceptance (completed in dev on 15 October 2026)

The maintainer recorded dev deployment and live evidence before closing Phase 1. Repository tests passing or Terraform apply completing alone is insufficient evidence for operational paths.

- Observe a scheduled poll, a new raw object, and a processor completion. Verify logs are still delivered to all three function-specific groups after narrowing IAM. A successful snapshot with no new accepted sightings is valid; freshness measures successful processing, not new sightings.
- Verify `/health`, latest sightings, combined region/species/date filters, and pagination through the deployed application. Confirm date-filtered requests return successful responses and observations from the requested UK calendar day. Check the homepage displays data and its processing timestamp.
- Confirm both queues have encryption and 14-day retention, each Lambda has its correct failure destination, log groups retain 30 days, and the completion metric receives data.
- A synthetic malformed asynchronous processor event was invoked in dev. It failed three times, was delivered to the processor DLQ with `RetriesExhausted`, raised the processor error and DLQ alarms, and produced a successful SNS operational-topic action. The synthetic message was inspected and deleted; normal raw-object processing also continued successfully during the test.
- Poller execution-failure, EventBridge delivery-failure, and stale-processing simulations were deliberately left as optional future resilience drills. They are not prerequisites for the Phase 1 product sign-off; if run later, use synthetic events and a planned recovery procedure, do not change credentials or expose source records to manufacture a failure, and record CloudWatch's observed timing.
- Email is optional. If configured, confirm the subscription and verify a problem notification reaches that address. Routine successful heartbeats must not generate notifications.

For manual replay, first fix the cause and determine the message envelope. EventBridge DLQ messages carry the original event with delivery metadata in message attributes; Lambda on-failure records wrap it in `requestPayload`. Replay only the original event to the correct function, verify success, and only then remove that specific DLQ message. Processor replay requires its raw S3 object to still exist; queue retention of 14 days does not extend raw S3 retention of one day. If the raw object has expired, a new poll can only recover observations still available from the upstream one-day window. Do not attach these queues directly to the current handlers as SQS event sources: their event envelopes differ. Never purge an entire queue as a substitute for reviewing failed events.

`ROADMAP.md` records the completed dev acceptance evidence. Continue to distinguish implemented code, deployed infrastructure, and directly verified behaviour in future phases.

## Python changes

For Python changes:

- keep dependencies explicit;
- preserve the Lambda entry point where applicable;
- handle external API failures deliberately;
- avoid hard-coded environment-specific configuration;
- add focused tests for new behaviour where practical.

Build all Lambda deployment packages from the repository root with `python build_lambdas.py`. The launcher runs the poller, processor, and read build scripts in sequence and stops on the first failure.

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
