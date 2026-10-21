# FinOps & Cost Management

## Current Monthly Cost Estimate

| Resource | SKU | Region | ~USD/month |
|----------|-----|--------|-----------|
| AKS (1 node DS2_v2) | Standard | EastAsia | ~$70 |
| ACA Environment (cae-portfolio-env) | Consumption | SEA | ~$0 (idle) |
| ACA smartdoc-api (0.5 vCPU) | Consumption | SEA | ~$8 |
| ACA kho-tra-sua-api (0.5 vCPU) | Consumption | SEA | ~$8 |
| ACR crportfolioa3deec (Basic) | Basic | SEA | ~$5 |
| ACR acrflashsalep6 (Basic) | Basic | SEA | ~$5 |
| Log Analytics Workspace | Pay-per-GB | SEA | ~$2 |
| Cloudflare Pages/Workers | Free | Global | $0 |
| **Total** | | | **~$98/month** |

## Cost Controls

### Scale-to-Zero (Container Apps)
```bash
# Scale smartdoc-api to 0 when not demoing
az containerapp update \
  --name smartdoc-api \
  --resource-group rg-portfolio-prod \
  --min-replicas 0 \
  --max-replicas 1
```

### AKS Node Pool Stop/Start
```bash
# Stop AKS when not in use (~$70/day saving)
az aks stop --name aks-portfolio-dev \
  --resource-group rg-aks-platform-dev

# Restart when needed
az aks start --name aks-portfolio-dev \
  --resource-group rg-aks-platform-dev
```

### Budget Alert
```bash
# Set $150/month budget alert
az consumption budget create \
  --budget-name portfolio-monthly-budget \
  --amount 150 \
  --time-grain Monthly \
  --time-period-start $(date +%Y-%m-01) \
  --time-period-end 2027-01-01 \
  --category Cost \
  --notifications "{'actual_GreaterThan_80_Percent':{'enabled':true,'operator':'GreaterThan','threshold':80,'contact-emails':['binhtan5734@gmail.com']}}"
```
