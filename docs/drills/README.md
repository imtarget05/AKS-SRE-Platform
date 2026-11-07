# Phase 14 — Reliability experiments

Each experiment follows Hypothesis -> Procedure -> TTR -> Evidence file.

| ID | Experiment | Target | Expected |
|---|---|---|---|
| R1 | Pod termination | payment-service | RTO <= 30s, no 5xx beyond retry |
| R2 | Kafka broker loss (1 of 3) | kafka | producer retries, no data loss (minISR=2) |
| R3 | RabbitMQ outage | rabbitmq | outbox buffers, replays after recovery |
| R4 | Redis outage | redis | login rate-limit fails closed (503), recovers |
| R5 | Postgres outage | postgres | readiness 503, recovers |
| R6 | Obs stack outage | monitoring | checkout still succeeds (obs must not gate traffic) |

Run: `scripts/run-drill.sh <ID>` (to be wired). Record output in docs/drills/evidence/.
