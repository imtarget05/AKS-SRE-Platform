# Self-Hosted Langfuse Observability on AKS

This folder provides Kubernetes manifests to deploy a private, self-hosted Langfuse server instance on Azure Kubernetes Service (AKS).

## Architecture
- **Namespace**: `langfuse`
- **Component**: `langfuse-server` (stateless web + API ingestion backend)
- **Image**: `ghcr.io/langfuse/langfuse:2.60.10`
- **Internal Service**: `langfuse-server.langfuse.svc.cluster.local:3000`

## Prerequisites
Create the `langfuse-secrets` secret containing your PostgreSQL database connection string and auth salt:
```bash
kubectl create secret generic langfuse-secrets -n langfuse \
  --from-literal=database-url="postgresql://langfuse:password@postgres:5432/langfuse" \
  --from-literal=nextauth-secret="$(openssl rand -hex 32)" \
  --from-literal=salt="$(openssl rand -hex 32)"
```

## Deployment via Kustomize
```bash
kubectl apply -k kubernetes/apps/langfuse/
```
