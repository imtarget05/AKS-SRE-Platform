import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from schemas.evidence_envelope import EvidenceEnvelope
from schemas.action_intent import ActionIntent, ExecutionReceipt


class StorageManager:
    """
    Lightweight, reliable SQLite storage for Agent Hub investigation state and evidence.
    Supports both file-based persistent database and in-memory test mode.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("AGENT_HUB_DB_PATH", "agent_hub.db")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS investigation_runs (
                    run_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    case_type TEXT NOT NULL,
                    entity_ref TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    request_hash TEXT,
                    state TEXT NOT NULL,
                    proposal_json TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_runs_idempotency ON investigation_runs(idempotency_key);

                CREATE TABLE IF NOT EXISTS evidence_records (
                    evidence_hash TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    case_type TEXT NOT NULL,
                    entity_ref TEXT NOT NULL,
                    source_service TEXT NOT NULL,
                    source_sha TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    record_version INTEGER NOT NULL,
                    observed_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    facts_json TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    redaction_level TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES investigation_runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS investigation_evidence (
                    run_id TEXT NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    PRIMARY KEY (run_id, evidence_hash),
                    FOREIGN KEY(run_id) REFERENCES investigation_runs(run_id),
                    FOREIGN KEY(evidence_hash) REFERENCES evidence_records(evidence_hash)
                );

                CREATE TABLE IF NOT EXISTS human_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES investigation_runs(run_id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS uq_human_decision_run ON human_decisions(run_id);

                CREATE TABLE IF NOT EXISTS action_intents (
                    intent_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    requested_by TEXT NOT NULL DEFAULT '',
                    command_type TEXT NOT NULL,
                    owner_service TEXT NOT NULL,
                    target_endpoint TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    entity_ref TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    risk_level TEXT NOT NULL,
                    state TEXT NOT NULL,
                    intent_hash TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES investigation_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_actions_idempotency ON action_intents(idempotency_key);
                CREATE INDEX IF NOT EXISTS idx_actions_run ON action_intents(run_id);

                CREATE TABLE IF NOT EXISTS action_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT UNIQUE NOT NULL,
                    decision TEXT NOT NULL,
                    approver_id TEXT NOT NULL,
                    approver_role TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    intent_hash TEXT NOT NULL,
                    approved_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(intent_id) REFERENCES action_intents(intent_id)
                );

                CREATE TABLE IF NOT EXISTS execution_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    intent_id TEXT UNIQUE NOT NULL,
                    owner_command_id TEXT,
                    idempotency_key TEXT NOT NULL,
                    executed_by TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    executed_at TIMESTAMP NOT NULL,
                    owner_status_code INTEGER NOT NULL,
                    before_state_json TEXT NOT NULL,
                    after_state_json TEXT NOT NULL,
                    verified BOOLEAN NOT NULL,
                    audit_ref TEXT NOT NULL,
                    result_summary TEXT NOT NULL,
                    FOREIGN KEY(intent_id) REFERENCES action_intents(intent_id)
                );
            """)

            # Schema migration guard for existing SQLite volumes
            cur = conn.execute("PRAGMA table_info(investigation_runs);")
            existing_cols = [row["name"] for row in cur.fetchall()]
            if "request_hash" not in existing_cols:
                conn.execute("ALTER TABLE investigation_runs ADD COLUMN request_hash TEXT;")
            action_cols = [row["name"] for row in conn.execute("PRAGMA table_info(action_intents);")]
            if "requested_by" not in action_cols:
                conn.execute("ALTER TABLE action_intents ADD COLUMN requested_by TEXT NOT NULL DEFAULT '';")
            conn.execute("""
                INSERT OR IGNORE INTO investigation_evidence (run_id, evidence_hash)
                SELECT run_id, evidence_hash FROM evidence_records
            """)

    def save_run(
        self,
        run_id: str,
        idempotency_key: str,
        case_type: str,
        entity_ref: str,
        scope_id: str,
        user_id: str,
        state: str,
        request_hash: Optional[str] = None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO investigation_runs
                (run_id, idempotency_key, case_type, entity_ref, scope_id, user_id, request_hash, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, idempotency_key, case_type, entity_ref, scope_id, user_id, request_hash, state, now, now))

    def get_run_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM investigation_runs WHERE idempotency_key = ?", (idempotency_key,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("proposal_json"):
                res["proposal"] = json.loads(res["proposal_json"])
            return res

    def update_run_state(self, run_id: str, state: str, proposal_json: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            if proposal_json is not None:
                conn.execute("""
                    UPDATE investigation_runs
                    SET state = ?, proposal_json = ?, updated_at = ?
                    WHERE run_id = ?
                """, (state, proposal_json, now, run_id))
            else:
                conn.execute("""
                    UPDATE investigation_runs
                    SET state = ?, updated_at = ?
                    WHERE run_id = ?
                """, (state, now, run_id))

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM investigation_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("proposal_json"):
                res["proposal"] = json.loads(res["proposal_json"])

            # Attach human decision if recorded
            dec_cur = conn.execute("SELECT * FROM human_decisions WHERE run_id = ? ORDER BY id DESC LIMIT 1", (run_id,))
            dec_row = dec_cur.fetchone()
            if dec_row:
                res["decision"] = dec_row["decision"]
                res["reviewer_id"] = dec_row["reviewer_id"]
                res["decision_reason"] = dec_row["reason"]
            return res

    def save_evidence(self, run_id: str, envelope: EvidenceEnvelope) -> None:
        """
        Saves evidence envelope with strict immutability.
        ON CONFLICT(evidence_hash) DO NOTHING preserves the original snapshot.
        Each run still gets its own association with that snapshot.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO evidence_records (
                    evidence_hash, run_id, case_type, entity_ref, source_service, source_sha,
                    scope_id, record_version, observed_at, expires_at, facts_json,
                    source_refs_json, classification, redaction_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_hash) DO NOTHING
            """, (
                envelope.evidence_hash,
                run_id,
                envelope.case_type,
                envelope.entity_ref,
                envelope.source_service,
                envelope.source_sha,
                envelope.scope_id,
                envelope.record_version,
                envelope.observed_at.isoformat(),
                envelope.expires_at.isoformat(),
                json.dumps(envelope.facts, sort_keys=True),
                json.dumps(envelope.source_refs),
                envelope.classification,
                envelope.redaction_level,
                now
            ))
            conn.execute("""
                INSERT OR IGNORE INTO investigation_evidence (run_id, evidence_hash)
                VALUES (?, ?)
            """, (run_id, envelope.evidence_hash))

    def get_evidences_for_run(self, run_id: str) -> List[EvidenceEnvelope]:
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT e.* FROM evidence_records e
                JOIN investigation_evidence r ON r.evidence_hash = e.evidence_hash
                WHERE r.run_id = ?
            """, (run_id,))
            rows = cur.fetchall()
            evidences = []
            for row in rows:
                evidences.append(EvidenceEnvelope(
                    case_type=row["case_type"],
                    entity_ref=row["entity_ref"],
                    source_service=row["source_service"],
                    source_sha=row["source_sha"],
                    scope_id=row["scope_id"],
                    record_version=row["record_version"],
                    observed_at=datetime.fromisoformat(row["observed_at"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]),
                    facts=json.loads(row["facts_json"]),
                    source_refs=json.loads(row["source_refs_json"]),
                    classification=row["classification"],
                    redaction_level=row["redaction_level"],
                    evidence_hash=row["evidence_hash"]
                ))
            return evidences

    def record_human_decision(self, run_id: str, decision: str, reviewer_id: str, reason: str) -> None:
        """
        Records human decision with single-decision invariant.
        A run that is already closed will reject duplicate decisions with HTTP 409 Conflict.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute("SELECT state FROM investigation_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
            if row["state"] == "closed":
                raise HTTPException(
                    status_code=409,
                    detail=f"Conflict: Investigation run '{run_id}' is already closed. Duplicate decisions are prohibited."
                )

            # Check if decision for run_id already exists
            cur = conn.execute("SELECT id FROM human_decisions WHERE run_id = ?", (run_id,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail=f"Conflict: A human decision has already been recorded for run '{run_id}'."
                )

            try:
                conn.execute("""
                    INSERT INTO human_decisions (run_id, decision, reviewer_id, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (run_id, decision, reviewer_id, reason, now))
                conn.execute("""
                    UPDATE investigation_runs
                    SET state = 'closed', updated_at = ?
                    WHERE run_id = ?
                """, (now, run_id))
            except sqlite3.IntegrityError:
                raise HTTPException(
                    status_code=409,
                    detail=f"Conflict: Human decision integrity violation on run '{run_id}'."
                )

    def recover_dangling_runs(self, timeout_minutes: int = 5) -> int:
        """
        Self-healing guard: Scan for runs stuck in intermediate states (received, authorized)
        older than timeout_minutes and transition them to 'abstained' to prevent orphaned runs.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute("""
                UPDATE investigation_runs
                SET state = 'abstained', updated_at = ?
                WHERE state IN ('received', 'authorized')
                AND (strftime('%s', 'now') - strftime('%s', created_at)) > (? * 60)
            """, (now, timeout_minutes))
            return cur.rowcount

    def save_intent(self, intent: ActionIntent) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO action_intents (
                    intent_id, run_id, requested_by, command_type, owner_service, target_endpoint,
                    scope_id, entity_ref, parameters_json, idempotency_key, risk_level,
                    state, intent_hash, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intent.intent_id,
                intent.run_id,
                intent.requested_by,
                intent.command_type,
                intent.owner_service,
                intent.target_endpoint,
                intent.scope_id,
                intent.entity_ref,
                json.dumps(intent.parameters),
                intent.idempotency_key,
                intent.risk_level,
                intent.state,
                intent.intent_hash,
                intent.created_at.isoformat(),
                intent.expires_at.isoformat()
            ))

    def get_intent(self, intent_id: str) -> Optional[ActionIntent]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM action_intents WHERE intent_id = ?", (intent_id,))
            row = cur.fetchone()
            if not row:
                return None
            return ActionIntent(
                intent_id=row["intent_id"],
                run_id=row["run_id"],
                requested_by=row["requested_by"],
                command_type=row["command_type"],
                owner_service=row["owner_service"],
                target_endpoint=row["target_endpoint"],
                scope_id=row["scope_id"],
                entity_ref=row["entity_ref"],
                parameters=json.loads(row["parameters_json"]),
                idempotency_key=row["idempotency_key"],
                risk_level=row["risk_level"],
                state=row["state"],
                intent_hash=row["intent_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"])
            )

    def get_intent_by_idempotency_key(self, idempotency_key: str) -> Optional[ActionIntent]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM action_intents WHERE idempotency_key = ?", (idempotency_key,))
            row = cur.fetchone()
            if not row:
                return None
            return ActionIntent(
                intent_id=row["intent_id"],
                run_id=row["run_id"],
                requested_by=row["requested_by"],
                command_type=row["command_type"],
                owner_service=row["owner_service"],
                target_endpoint=row["target_endpoint"],
                scope_id=row["scope_id"],
                entity_ref=row["entity_ref"],
                parameters=json.loads(row["parameters_json"]),
                idempotency_key=row["idempotency_key"],
                risk_level=row["risk_level"],
                state=row["state"],
                intent_hash=row["intent_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"])
            )

    def update_intent_state(self, intent_id: str, state: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE action_intents SET state = ? WHERE intent_id = ?", (state, intent_id))

    def claim_intent_execution(self, intent_id: str) -> bool:
        """Only one executor may move an approved/uncertain intent into execution."""
        with self._get_connection() as conn:
            changed = conn.execute(
                "UPDATE action_intents SET state = 'EXECUTING' "
                "WHERE intent_id = ? AND state IN ('APPROVED', 'UNKNOWN')",
                (intent_id,),
            )
            return changed.rowcount == 1

    def record_action_approval(
        self,
        intent_id: str,
        decision: str,
        approver_id: str,
        approver_role: str,
        reason: str,
        intent_hash: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO action_approvals (
                    intent_id, decision, approver_id, approver_role, reason, intent_hash, approved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (intent_id, decision, approver_id, approver_role, reason, intent_hash, now))

    def get_action_approval(self, intent_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM action_approvals WHERE intent_id = ?", (intent_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def save_execution_receipt(self, receipt: ExecutionReceipt) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO execution_receipts (
                    receipt_id, intent_id, owner_command_id, idempotency_key,
                    executed_by, approved_by, executed_at, owner_status_code,
                    before_state_json, after_state_json, verified, audit_ref, result_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                receipt.receipt_id,
                receipt.intent_id,
                receipt.owner_command_id,
                receipt.idempotency_key,
                receipt.executed_by,
                receipt.approved_by,
                receipt.executed_at.isoformat(),
                receipt.owner_status_code,
                json.dumps(receipt.before_state),
                json.dumps(receipt.after_state),
                receipt.verified,
                receipt.audit_ref,
                receipt.result_summary
            ))

    def get_execution_receipt(self, intent_id: str) -> Optional[ExecutionReceipt]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM execution_receipts WHERE intent_id = ?", (intent_id,))
            row = cur.fetchone()
            if not row:
                return None
            return ExecutionReceipt(
                receipt_id=row["receipt_id"],
                intent_id=row["intent_id"],
                owner_command_id=row["owner_command_id"],
                idempotency_key=row["idempotency_key"],
                executed_by=row["executed_by"],
                approved_by=row["approved_by"],
                executed_at=datetime.fromisoformat(row["executed_at"]),
                owner_status_code=row["owner_status_code"],
                before_state=json.loads(row["before_state_json"]),
                after_state=json.loads(row["after_state_json"]),
                verified=bool(row["verified"]),
                audit_ref=row["audit_ref"],
                result_summary=row["result_summary"]
            )
