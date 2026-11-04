# AKS open-item decisions for release review

This document records what can be closed locally and what still requires an
owner or a VNet-connected execution environment. It does not claim that a
cluster mutation was performed.

| Item | Local disposition | Required next action |
|---|---|---|
| Label drift | Keep as an explicit accepted finding; no silent self-heal change was introduced | Owner chooses accept-and-monitor or approves a reconciliation mechanism |
| Second Argo CD in `default` | Keep as an environment finding; repository bootstrap does not silently remove it | Inspect the live cluster and approve removal/migration |
| Legacy `kubernetes/` root dry-run | Keep separate from the maintained GitOps scope; KEDA webhook rejection is documented | Decide whether to retire the root or maintain a separately validated profile |
| External repositories | `NOT_PRESENT`, not pass | Provide exact checkouts/revisions to the validator |
| Live sync/apply | Not executed | Run from inside the private-link VNet and capture Argo status, revision, health, and drift |

## Interview-safe statement

The platform has strong offline and historical Azure evidence plus regression
gates, but current live acceptance is intentionally blocked until the private
cluster is accessed from the correct network and the ownership decisions above
are approved.
