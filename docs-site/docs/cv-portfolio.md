# Four-project portfolio — interview map

Each product addresses a separate business problem. These are the paths to
the owning evidence; this AKS site does not certify another repo's current
deployment, CI, test count, or security scan.

| Product | Business question | Evidence boundary |
|---|---|---|
| [OpsBridge](https://github.com/imtarget05/OpsBridge) | Can flash-sale orders avoid oversell and can operations reconcile asynchronous events? | Concurrency, Saga, outbox/inbox and operational review live in its own repository. |
| [QuanLyKho](https://github.com/imtarget05/QuanLyKho) | Can a tea shop control lot/expiry inventory and require a different human checker before posting? | FastAPI/PostgreSQL are business authority; AI is advisory. |
| [SmartDocumentChatbot](https://github.com/imtarget05/Smart-Document-Chatbot) | Can a user ask questions over owned documents with citations and a safe refusal? | The live RAG path and experimental agent path require separate verification. |
| [AKS-SRE-Platform](https://github.com/imtarget05/AKS-SRE-Platform) | Can a team review platform changes and prove what ran on Azure versus local kind? | Historical transient AKS evidence, local GitOps/observability proof, explicit non-claims. |

## AKS/SRE claim to defend

The platform validated node placement, ACR digest pull and token exchange
on transient AKS, then deleted the cluster. GitOps reconciliation, Gateway
API and alert fire/resolve were measured on local kind. Autoscaler, enforced
NetworkPolicy, DR and production SLO history remain unverified.

See the [cross-repository interview guide](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/PORTFOLIO_INTERVIEW_CHEATSHEET.md)
and [AKS claim matrix](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/portfolio-audit-2026-10-21.md).
