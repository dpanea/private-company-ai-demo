from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any

from pcad.config import Settings
from pcad.db import connect_dict
from pcad.models import ProactiveAlert


class ProactiveAlertGenerator:
    """Generates deterministic proactive alerts for an account."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_for_account(self, account_id: str, *, session_id: str | None = None) -> list[ProactiveAlert]:
        with connect_dict(self.settings) as conn:
            today = _reference_date(conn)
            alerts = []
            alerts.extend(_approaching_close_date(conn, account_id, today))
            alerts.extend(_stalled_account(conn, account_id, today))
            alerts.extend(_unresolved_objection(conn, account_id, session_id))
            alerts.extend(_missing_followup(conn, account_id, today))
            alerts.extend(_champion_positive_signal(conn, account_id, session_id, today))
            alerts.extend(_data_inconsistency(conn, account_id))
            conn.execute(
                "DELETE FROM proactive_alerts WHERE account_id = %s AND session_id IS NOT DISTINCT FROM %s",
                (account_id, session_id),
            )
            for alert in alerts:
                conn.execute(
                    """
                    INSERT INTO proactive_alerts (
                        alert_id, account_id, session_id, alert_type, severity, title, body_markdown,
                        evidence_doc_ids, evidence_artifact_ids, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        alert.alert_id,
                        alert.account_id,
                        session_id,
                        alert.alert_type,
                        alert.severity,
                        alert.title,
                        alert.body_markdown,
                        alert.evidence_doc_ids,
                        alert.evidence_artifact_ids,
                        alert.created_at,
                    ),
                )
            conn.commit()
            return alerts


def _reference_date(conn: Any) -> date:
    row = conn.execute(
        """
        SELECT max(value)::date AS reference_date
        FROM (
            SELECT metadata->>'reference_date' AS value FROM raw_artifacts WHERE metadata ? 'reference_date'
            UNION ALL
            SELECT metadata_json->>'reference_date' AS value FROM rag_documents WHERE metadata_json ? 'reference_date'
        ) AS refs
        WHERE value IS NOT NULL
        """
    ).fetchone()
    return row["reference_date"] if row and row["reference_date"] else date.today()


def _new_alert(
    account_id: str,
    alert_type: str,
    severity: str,
    title: str,
    body: str,
    *,
    doc_ids: list[str] | None = None,
    artifact_ids: list[str] | None = None,
) -> ProactiveAlert:
    key = "|".join([account_id, alert_type, title, body, ",".join(doc_ids or []), ",".join(artifact_ids or [])])
    return ProactiveAlert(
        alert_id=f"alert:{hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]}",
        account_id=account_id,
        alert_type=alert_type,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        title=title,
        body_markdown=body,
        evidence_doc_ids=doc_ids or [],
        evidence_artifact_ids=artifact_ids or [],
        created_at=datetime.now(timezone.utc),
    )


def _approaching_close_date(conn: Any, account_id: str, today: date) -> list[ProactiveAlert]:
    rows = conn.execute(
        """
        SELECT opportunity_id, name, close_date, is_closed
        FROM opportunities
        WHERE account_id = %s AND coalesce(is_closed, false) = false AND close_date <= %s
        ORDER BY close_date
        """,
        (account_id, today + timedelta(days=14)),
    ).fetchall()
    alerts = []
    for row in rows:
        days = (row["close_date"] - today).days if row["close_date"] else 999
        if days <= 0:
            severity = "critical"
        elif days <= 7:
            severity = "warning"
        else:
            severity = "info"
        alerts.append(
            _new_alert(
                account_id,
                "approaching_close_date",
                severity,
                "Opportunity close date needs attention",
                f"{row['name']} closes on {row['close_date']}. Review next steps and confirm whether the opportunity is still on track. [Source: Opportunity {row['opportunity_id']}]",
            )
        )
    return alerts


def _stalled_account(conn: Any, account_id: str, today: date) -> list[ProactiveAlert]:
    row = conn.execute("SELECT max(activity_date) AS last_activity FROM activities WHERE account_id = %s", (account_id,)).fetchone()
    last_activity = row["last_activity"] if row else None
    if last_activity and last_activity >= today - timedelta(days=14):
        return []
    body = "No CRM activity is recorded for this account in the last 14 days. Check whether follow-up is needed."
    if last_activity:
        body += f" Last activity was on {last_activity}."
    return [_new_alert(account_id, "stalled_account", "warning", "Account has gone quiet", body)]


def _unresolved_objection(conn: Any, account_id: str, session_id: str | None) -> list[ProactiveAlert]:
    rows = conn.execute(
        """
        SELECT doc_id, title, content_markdown, source_record_ids,
               coalesce(last_source_updated_at, generated_at) AS objection_at
        FROM rag_documents
        WHERE account_id = %s
          AND (session_id IS NULL OR session_id = %s)
          AND doc_type IN ('email_thread_summary', 'meeting_summary')
          AND content_markdown ~* '(concern|objection|blocker|issue with|worried about|blocked)'
        ORDER BY objection_at
        """,
        (account_id, session_id),
    ).fetchall()
    alerts = []
    for row in rows:
        later = conn.execute(
            """
            SELECT 1 FROM activities
            WHERE account_id = %s
              AND activity_date > %s::timestamptz
              AND coalesce(description, '') || ' ' || coalesce(subject, '') ~* '(resolved|addressed|answered|followed up)'
            ORDER BY activity_date ASC
            LIMIT 1
            """,
            (account_id, row["objection_at"]),
        ).fetchone()
        if later:
            continue
        artifact_ids = [item for item in row["source_record_ids"] or [] if ":" in item]
        alerts.append(
            _new_alert(
                account_id,
                "unresolved_objection",
                "warning",
                "Unresolved objection detected",
                f"{row['title']} includes a concern or blocker and no later resolving activity was found. Review the objection and follow up with a concrete answer. [Source: {row['doc_id']}]",
                doc_ids=[row["doc_id"]],
                artifact_ids=artifact_ids,
            )
        )
    return alerts


def _missing_followup(conn: Any, account_id: str, today: date) -> list[ProactiveAlert]:
    rows = conn.execute(
        """
        SELECT activity_id, subject, activity_date
        FROM activities
        WHERE account_id = %s AND priority = 'High' AND coalesce(status, '') <> 'Completed' AND activity_date < %s
        ORDER BY activity_date
        """,
        (account_id, today - timedelta(days=5)),
    ).fetchall()
    return [
        _new_alert(
            account_id,
            "missing_followup",
            "warning",
            "High-priority follow-up is overdue",
            f"{row['subject'] or row['activity_id']} has been open since {row['activity_date']}. Close the loop or update the task owner. [Source: Task {row['activity_id']}]",
        )
        for row in rows
    ]


def _champion_positive_signal(conn: Any, account_id: str, session_id: str | None, today: date) -> list[ProactiveAlert]:
    cutoff = today - timedelta(days=14)
    rows = conn.execute(
        """
        SELECT doc_id, title, content_markdown, source_record_ids, generated_at
        FROM rag_documents
        WHERE account_id = %s
          AND (session_id IS NULL OR session_id = %s)
          AND doc_type IN ('email_thread_summary', 'meeting_summary')
          AND coalesce(last_source_updated_at, generated_at) >= %s::timestamptz
          AND content_markdown ~* '(let''s move forward|ready to proceed|looks great|approved by|we''re on board)'
        ORDER BY generated_at DESC
        LIMIT 3
        """,
        (account_id, session_id, cutoff),
    ).fetchall()
    alerts = []
    for row in rows:
        alerts.append(
            _new_alert(
                account_id,
                "champion_positive_signal",
                "info",
                "Positive buying signal",
                f"{row['title']} contains a strong positive signal from the account. Use it to advance the next step while the momentum is current. [Source: {row['doc_id']}]",
                doc_ids=[row["doc_id"]],
                artifact_ids=[item for item in row["source_record_ids"] or [] if ":" in item],
            )
        )
    return alerts


def _data_inconsistency(conn: Any, account_id: str) -> list[ProactiveAlert]:
    rows = conn.execute(
        """
        SELECT o.opportunity_id, o.name, o.stage, o.is_won, o.is_closed
        FROM opportunities o
        LEFT JOIN contracts c ON c.opportunity_id_if_available = o.opportunity_id OR c.contract_id = o.contract_id
        WHERE o.account_id = %s AND ((o.stage = 'Closed Won' AND c.contract_id IS NULL) OR (o.is_won = true AND coalesce(o.is_closed, false) = false))
        """,
        (account_id,),
    ).fetchall()
    return [
        _new_alert(
            account_id,
            "data_inconsistency",
            "info",
            "CRM data inconsistency",
            f"{row['name']} has inconsistent close/won/contract data. Review the opportunity record before relying on automation. [Source: Opportunity {row['opportunity_id']}]",
        )
        for row in rows
    ]
