# Preview runtime defect — 2026-11-04

The first Cloudflare Pages preview at source `bf9289b` deployed successfully but failed browser runtime verification. The build emitted five separately minified **classic** scripts with colliding top-level names; browser console showed `Identifier ... has already been declared`. Empty tab placeholders delayed chart/event DOM creation, and inline click handlers were blocked by the strict CSP. A static file existence smoke test did not cover these behaviors. No production Pages deployment was changed.

Correction at `8437b0f`: build-time tab insertion, isolated module scripts, delegated handlers, null-safe edge probe, and a build artifact smoke check for the entry page, tabs, data feed, module tags, CSP-compatible handlers and embedded SHA. The replacement Preview deployment `f600044d-9ce7-4a2d-9689-9176f6f5b986` passed browser interaction and console-error checks. Azure workload telemetry remains unverified and is labeled accordingly.
