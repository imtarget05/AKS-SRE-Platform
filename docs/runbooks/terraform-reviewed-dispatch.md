# Reviewed Terraform dispatch (code contract; cloud exercise pending)

The public repository's `AKS Deploy` workflow accepts only manual `plan`,
`apply`, or `destroy` dispatch. The first job builds a local Terraform plan and
publishes a SHA-256 fingerprint of the complete canonical JSON plan, excluding
only its generation timestamp. It also publishes a short allowlisted review
table: resource address, action, region, SKU, VM size, and node counts. The
raw binary and JSON plan stay on the ephemeral runner and are never uploaded
as artifacts or written to logs.

For `apply` or `destroy`, the next job waits at the GitHub `production`
environment gate. After approval it builds a fresh local plan at the same
workflow commit and compares the complete fingerprint. Any state drift,
different value, provider nondeterminism, or missing fingerprint blocks the
apply. The operator must dispatch a new run and review it again. Both local
`rebuild-aks.sh apply` and `destroy` paths are disabled.

The review table intentionally omits secret and arbitrary provider fields.
Review the code diff, provider lockfile, affected resource addresses, region,
SKU and count changes, and the expected cost and blast radius before approval.
If the omitted fields matter, use an approved private channel to inspect the
plan; do not publish raw plan artifacts in this public repository. A matching
fingerprint proves that the execution plan has the same JSON values as the
plan job, not that the plan is beneficial or safe.

**Approval ownership:** This is currently a one-person portfolio workflow.
The YAML's `environment: production` declares a gate, but it does not prove
that an independent reviewer is configured. Before any cloud action, inspect
the GitHub environment settings, require a separate qualified reviewer, and
disable self-approval where the account/plan supports it. Until that is
verified, describe the workflow as manually gated and self-reviewed, never as
independent dual control or production operational evidence.

The current implementation has only offline tests. No cloud apply or destroy
was performed to validate this release path.
