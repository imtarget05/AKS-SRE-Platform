# Architecture Overview

## Hub-Spoke Landing Zone on Azure

```mermaid
flowchart TD
    subgraph AZURE["Microsoft Azure — Portfolio Landing Zone"]
        subgraph EA["East Asia Region"]
            subgraph RG_AKS["rg-aks-platform-dev"]
                AKS["AKS: aks-portfolio-dev\nKubernetes v1.36 | 1 node DS2_v2\nWorkload Identity Enabled"]
                OIDC["OIDC Issuer\nhttps://eastasia.oic.prod-aks.azure.com"]
                subgraph NS["Namespaces"]
                    NS_FS["flashsale\nFlashSale API + Worker"]
                    NS_LA["legacyapp\nLegacy Inventory App"]
                end
            end
        end
        subgraph SEA["Southeast Asia Region"]
            subgraph RG_PROD["rg-portfolio-prod"]
                ACA_ENV["ACA Environment\ncae-portfolio-env"]
                ACA1["smartdoc-api\nSpring Boot 3 :8080"]
                ACR["crportfolioa3deec.azurecr.io\nBasic SKU"]
            end
            subgraph RG_FS["rg-flashsale"]
                ACR2["acrflashsalep6.azurecr.io"]
                ACA2["kho-tra-sua-api\nFastAPI :8000"]
            end
        end
        ENTRA["Microsoft Entra ID\nOIDC Federation"]
        MI["Managed Identity\nmi-aks-wi-proof-dev"]
    end
    subgraph CF["Cloudflare (Free Tier)"]
        P1["smart-doc-chatbot.pages.dev"]
        P2["opsbridge-dashboard.pages.dev"]
        P3["quan-ly-kho-tra-sua.workers.dev"]
        P4["aks-sre-platform.pages.dev"]
    end
    subgraph GH["GitHub Actions CI/CD"]
        CI1["SmartDoc CI/CD"]
        CI2["FlashSale DevSecOps"]
        CI3["QuanLyKho Pipeline"]
        CI4["AKS-SRE GitOps"]
    end
    P1 --> ACA1
    P3 --> ACA2
    GH --> CF
    GH --> ACA1
    GH --> ACA2
    CI4 --> AKS
    AKS --> ENTRA
    ENTRA --> MI
    MI --> ACR
    AKS --> NS_FS & NS_LA
```

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Container Runtime | AKS (eastasia) + ACA (southeastasia) | AKS for GitOps workloads, ACA for scale-to-zero cost savings |
| Registry | ACR Basic SKU | Managed, integrated with AKS via Kubelet Identity |
| Identity | Workload Identity Federation | Zero static secrets — production security pattern |
| Frontend | Cloudflare Pages/Workers | Free tier, global CDN, permanent URLs for CV |
| Event Bus | Kafka (Azure Event Hubs compatible) | Enterprise async pattern for RAG ingestion |
| GitOps | ArgoCD on AKS | Industry standard for K8s continuous delivery |

## ADR Log

- **ADR-012**: Azure first verification — SE-Asia SKUs subscription-blocked, eastasia chosen
- **ADR-014**: AKS over kind for production evidence — real Azure clusters required
- **ADR-015**: Scale-to-zero on ACA for cost control during portfolio phase
