# Incident Response Runbook

!!! warning "Production Incident Response — SRE Standard"
    Thời gian phản ứng: P0 < 15 phút, P1 < 1 giờ, P2 < 4 giờ

## 1. Phát Hiện Sự Cố (Detection)

```bash
# Kiểm tra trạng thái cluster
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running

# Kiểm tra events gần đây
kubectl get events --sort-by='.lastTimestamp' -A | tail -20

# Kiểm tra Container Apps
az containerapp show --name smartdoc-api --resource-group rg-portfolio-prod \
  --query "properties.runningStatus" -o tsv
```

## 2. Phân Loại Sự Cố (Classification)

| Mức Độ | Tiêu Chí | SLA |
|--------|----------|-----|
| **P0 — Critical** | Service down, data loss risk | 15 phút |
| **P1 — High** | Degraded performance, partial outage | 1 giờ |
| **P2 — Medium** | Single feature broken | 4 giờ |
| **P3 — Low** | Non-critical issue | 24 giờ |

## 3. Quy Trình Xử Lý (Response)

### Bước 1: Acknowledge & Communicate
```bash
# Tạo incident channel (Slack/Teams)
# Thông báo: "Incident P{level} - {summary} - Investigating"
# Assign Incident Commander (IC)
```

### Bước 2: Rollback (Nếu Cần)

```bash
# Rollback AKS deployment
kubectl rollout undo deployment/flashsale-api -n flashsale

# Rollback Container App revision
az containerapp revision list --name smartdoc-api \
  --resource-group rg-portfolio-prod -o table

az containerapp ingress traffic set --name smartdoc-api \
  --resource-group rg-portfolio-prod \
  --revision-weight <previous-revision>=100
```

### Bước 3: Root Cause Analysis (RCA)

```bash
# Thu thập logs
kubectl logs -l app=flashsale-api -n flashsale --since=1h > incident-logs.txt

# Azure Monitor
az monitor activity-log list \
  --resource-group rg-portfolio-prod \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  -o table
```

## 4. Post-Incident Review

- Blameless postmortem trong 48h sau incident
- Timeline đầy đủ (detection → resolution)
- Root cause + contributing factors
- Action items với owner và deadline
- Cập nhật runbook nếu cần
