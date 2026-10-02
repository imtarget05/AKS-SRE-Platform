# B3' — Azure provider registration

```text
measured_at : 2026-10-02T09:34:28Z
subscription: a3deec78-7edb-41cd-9e94-ec1d4d9379f5
method      : az provider show / az provider register, polled
```

| Provider | Before | After |
|---|---|---|
| `Microsoft.Insights` | `Registered` (already) | `Registered` |
| `Microsoft.Monitor` | `NotRegistered` | **`Registered`** |
| `Microsoft.Dashboard` | `NotRegistered` | **`Registered`** |

Only those two were registered. `Microsoft.Insights` was already registered when
re-checked, so it was left alone — re-registering a registered provider would
have been a mutation with no effect.

Registration reached `Registered` after 4 bounded polls at 30s
(`Microsoft.Dashboard` settled one poll before `Microsoft.Monitor`).

Sanity check after registration — the four providers the existing workloads
already depend on are untouched: `Microsoft.ContainerService`, `Microsoft.App`,
`Microsoft.OperationalInsights` and `Microsoft.Storage` all read `Registered`.

```text
PROVIDER_PREREQUISITE = VERIFIED_LIVE
```

This is a **prerequisite**, not a capability. Registering a provider does not
create a Managed Prometheus workspace, a Grafana instance or an alert rule. See
`docs/evidence/phase7b/` for what remains unverified.

```text
OBSERVABILITY = NOT_VERIFIED
```

## B4' — one policy gate was present but switched off

The audit found `scripts/policy-gate.py` enforcing image-digest policy behind an
opt-in flag, while `.github/workflows/pr-gate.yaml` invoked it as:

```yaml
- name: static policy and image gate
  run: python3 scripts/policy-gate.py
```

No flag. So `digest_required=False` on every CI run.

**Verified by mutation, not by reading the code.** An image reference was
rewritten to `:latest` and the gate was run locally:

```text
before fix:  POLICY GATE PASS: 2 kustomize root(s), 26 object(s), digest_required=False
             rc=0        <- a mutable tag passed the image policy
```

`:latest` was in fact still caught, but by a *different* rule (`image-tag`).
That is not a defence of the flag — it means the digest check had been
unenforced and was only incidentally masked. `deploy/base` ships `sre-demo-api:0.1.0`,
a pinned non-floating tag, which the digest check would have rejected; the gate
was green only because the check enforcing the stricter property was off.

The flag is now documented for what it actually is: `--require-digest` answers
"is this rendered output digest-pinned?", which is a question about a
deploy-time artifact where the digest is knowable. It is not a default, because
`deploy/base` cannot ship a digest it has not built. A mutable tag remains
rejected unconditionally.

Both readings are now covered by controls rather than by intent.

## Negative controls re-run locally

Each mutation applied to the canonical tree, gate executed, tree restored, and
the restored tree re-verified green:

| Control | Mutation | Result |
|---|---|---|
| M1 | image tag → `:latest` | `rc=1` — `[image-tag] … uses a mutable :latest tag` |
| M2 | `livenessProbe` removed | `rc=1` — `[probes] … containers ['sre-demo-api'] have no livenessProbe` |
| M3 | unclassified manifest added under `kubernetes/` | `rc=1` — `[manifest-inventory] … unclassified: add it to MANIFEST-INVENTORY.md` |

Every one failed **for its intended reason**, naming the rule that caught it —
not merely failing.

`python3 tests/test_gates.py` → **17 passed, 0 failed, 17 assertions total**.

## Historical evidence is untouched

`docs/evidence/phase7a/` still stands as it did, tied to its own commit and its
own configuration:

```text
19 runtime gates PASS on 2026-09-21, ~$0.20 compute
  user-pool placement · ACR pull by digest · Workload Identity token exchange
  · AcrPull · clean teardown
```

B4' does not refresh that, and nothing in this branch claims it does. It is
`VERIFIED_TRANSIENT` evidence for the configuration it was gathered against. A
new live Azure run is `NONE` here.

```text
TERRAFORM_NATIVE_TESTS = NOT_IMPLEMENTED
```

`find . -name '*.tftest.hcl'` returns 0. The CI step reports this and exits 1 on
purpose: `Success! 0 passed, 0 failed` is indistinguishable from a real pass by
exit code, and this repo refuses to treat it as one.