# Agent Hub SQLite connection lifecycle

## Source plan

Derived from the P1.3 Agent Hub storage item in the technical handoff.

## User journey

As an Agent Hub operator, I want storage operations to close SQLite connections
after success or failure, so that repeated requests do not leak database
resources.

## Task report

| Behavior | Validation | Result |
|---|---|---|
| Successful storage operations close every connection, including initialization | `python3 -m pytest --no-cov tests/test_storage_connection_lifecycle.py -q -W error::ResourceWarning` | PASS, 2 tests |
| Failed writes close their connection and preserve the integrity error | Same focused command | PASS, 2 tests |
| Agent Hub suite passes with resource warnings treated as errors | `python3 -m pytest -W error::ResourceWarning` | PASS, 63 tests |
| Agent Hub suite meets the configured coverage threshold | Same full-suite command | PASS, 85.48% total coverage (75% required) |

### RED/GREEN evidence

- RED: the new lifecycle tests failed because open connections remained
  executable after normal and duplicate-write operations. Python also emitted
  `ResourceWarning: unclosed database`.
- GREEN: a SQLite connection subclass now closes on context exit after preserving
  SQLite's normal commit/rollback behavior. Both focused tests and the full suite
  pass with `ResourceWarning` treated as an error.

## Coverage and known gaps

The full suite reported 85.48% total coverage. PostgreSQL support through
`DATABASE_URL` remains unimplemented; this change addresses SQLite connection
lifecycle only. PostgreSQL integration requires a dialect-aware schema/query
implementation and a PostgreSQL-backed validation environment.
