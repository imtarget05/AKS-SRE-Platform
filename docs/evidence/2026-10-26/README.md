# HPA Scale Drill — 2026-10-26

## Mục tiêu
Tạo scale event thật của HPA `opsbridge-api` (ns `flashsale`) và thu thập evidence UTC bằng
`scripts/log_scale_events.py` (read-only snapshots, JSONL).

## Kube context
`aks-portfolio-dev` — cluster AKS 2 nodes, cả hai thuộc agent pool `sys`
(`aks-sys-20053029-vmss000000`, `aks-sys-20053029-vmss000001`).

## Các bước thực hiện (UTC)
1. **Baseline** — 3 snapshots cách nhau 8s vào `hpa-scale-drill.jsonl`:
   `10:07:53Z`, `10:08:02Z`, `10:08:12Z` — HPA 2/2 replicas, cpu 6–7%/70%.
2. **Load CPU có kiểm soát** — `kubectl exec` vào pod app
   `opsbridge-api-6754cf4f66-6wtct` chạy CPU burner `sh` busy-loop, tự kết thúc sau 180s
   (bắt đầu ~10:10:30Z, kết thúc ~10:13:30Z). Không tạo pod mới, không sửa resource.
3. **Logger định kỳ** — chạy background `log_scale_events.py --samples 30 --interval-seconds 20`
   từ 10:09:53Z đến ~10:19:53Z (35 snapshots tổng, gồm baseline).
4. **Kết thúc** — xác nhận HPA về 2/2, capture 2 snapshot cuối (`10:20:37Z`, `10:20:47Z`).

## Scale events quan sát được (từ kubectl events + HPA status, KHÔNG bịa)
| Thời gian (UTC) | Event | Chi tiết |
|---|---|---|
| 10:09:15Z | `SuccessfulRescale` + `ScalingReplicaSet` | Scale up **2 → 3**, reason: cpu resource utilization above target |
| 10:10:00Z | `SuccessfulRescale` + `ScalingReplicaSet` | Scale up **3 → 5** (max), reason: cpu resource utilization above target |
| 10:13:43Z | `Scheduled` | Pod `opsbridge-api-6754cf4f66-d4vd2` được schedule lên `aks-sys-20053029-vmss000000` |
| 10:13:43Z–10:14:10Z | `FailedScheduling` (x nhiều lần) | `0/2 nodes are available: 1 Insufficient cpu, 1 Too many pods` — các pod scale-up còn lại **Pending** |
| 10:17:31Z | `SuccessfulRescale` + `ScalingReplicaSet` | Scale down **5 → 2**, reason: All metrics below target |

## Timeline HPA (desired/current)
- 10:07:53Z → 2/2 (baseline)
- 10:09:55Z → 3/3 (lastScale 10:09:15Z)
- 10:10:16Z → 5/5 (lastScale 10:10:00Z)
- 10:17:50Z → 2/2 (lastScale 10:17:31Z — HPA tự scale down sau khi load tắt + stabilization window)

## Limitations
- **Cluster chỉ 2 nodes (agent pool `sys`), không đủ CPU capacity**: HPA desired=5 nhưng chỉ
  2–3 pod Running; 3 pod ở trạng thái Pending với `FailedScheduling: 1 Insufficient cpu,
  1 Too many pods`. Không có node mới được cấp (cluster autoscaler không scale node pool `sys`).
- Pod `cpu-stress` (966m) đã tồn tại trong ns `flashsale` **trước khi drill bắt đầu** — không
  phải do drill tạo, không bị can thiệp; nó góp phần chiếm CPU node.
- HPA metric phản hồi chậm ~15–60s (metrics-server scrape interval) — giữa lúc load tăng và
  `SuccessfulRescale` event có độ trễ quan sát được.
- Scale-up và scale-down đều là HPA tự động (không dùng manual scale).

## Files
- `hpa-scale-drill.jsonl` — 35 JSONL snapshots (baseline → load → scale down → final), mỗi dòng
  chứa `captured_at_utc`, HPA status, user nodes, scale/schedule events.
