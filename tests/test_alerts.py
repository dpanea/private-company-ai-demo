"""One test per ProactiveAlertGenerator alert type, plus suppression checks.

Every alert is generated from CRM + rag_documents rows via real SQL. The
reference date is fixed at REFERENCE_DATE (= 2026-05-15) by injecting it into
one rag_document's metadata_json — that's the mechanism the production code
already uses to choose "today" deterministically.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pcad.retrieval.alerts import ProactiveAlertGenerator

from tests._seed import (
    REFERENCE_DATE,
    fetch_alerts,
    make_settings,
    seed_account,
    seed_activity,
    seed_contract,
    seed_opportunity,
    seed_rag_document,
    seed_user,
)


def _pin_reference_date(settings, *, account_id: str = "ACC_REF", doc_suffix: str = "anchor") -> None:
    """Drop one document carrying reference_date metadata so the generator's
    `_reference_date` helper returns REFERENCE_DATE."""
    seed_rag_document(
        settings,
        doc_id=f"reference_anchor:{doc_suffix}",
        account_id=account_id,
        doc_type="account_memory",
        title="Reference date anchor",
        content="anchor",
        include_reference_date=True,
    )


# ---------------------------------------------------------------------------
# approaching_close_date
# ---------------------------------------------------------------------------


def test_alert_approaching_close_date_severity_escalates_with_proximity(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_CD", account_name="Close Date Account")
    _pin_reference_date(settings, account_id="ACC_CD")

    # 12 days out → info, 3 days → warning, today → critical, 30 days → not flagged.
    seed_opportunity(
        settings, opportunity_id="OPP_INFO", account_id="ACC_CD",
        name="Info opportunity", close_date=REFERENCE_DATE + timedelta(days=12),
    )
    seed_opportunity(
        settings, opportunity_id="OPP_WARN", account_id="ACC_CD",
        name="Warning opportunity", close_date=REFERENCE_DATE + timedelta(days=3),
    )
    seed_opportunity(
        settings, opportunity_id="OPP_CRIT", account_id="ACC_CD",
        name="Critical opportunity", close_date=REFERENCE_DATE,
    )
    seed_opportunity(
        settings, opportunity_id="OPP_FAR", account_id="ACC_CD",
        name="Far away", close_date=REFERENCE_DATE + timedelta(days=30),
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_CD")
    alerts = [a for a in fetch_alerts(settings, "ACC_CD") if a["alert_type"] == "approaching_close_date"]

    severities = {alert["title"][:30] + alert["severity"]: alert["severity"] for alert in alerts}
    bodies = "\n".join(a["body_markdown"] for a in alerts)
    assert "OPP_INFO" in bodies
    assert "OPP_WARN" in bodies
    assert "OPP_CRIT" in bodies
    assert "OPP_FAR" not in bodies
    assert {a["severity"] for a in alerts} == {"info", "warning", "critical"}


# ---------------------------------------------------------------------------
# stalled_account
# ---------------------------------------------------------------------------


def test_alert_stalled_account_fires_when_quiet_more_than_14_days(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_QUIET", account_name="Quiet Account")
    _pin_reference_date(settings, account_id="ACC_QUIET")
    seed_activity(
        settings, activity_id="ACT_OLD", account_id="ACC_QUIET",
        activity_date=REFERENCE_DATE - timedelta(days=30),
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_QUIET")
    types = {a["alert_type"] for a in fetch_alerts(settings, "ACC_QUIET")}
    assert "stalled_account" in types


def test_alert_stalled_account_does_not_fire_when_recent_activity_exists(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_LIVE", account_name="Active Account")
    _pin_reference_date(settings, account_id="ACC_LIVE")
    seed_activity(
        settings, activity_id="ACT_RECENT", account_id="ACC_LIVE",
        activity_date=REFERENCE_DATE - timedelta(days=2),
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_LIVE")
    types = {a["alert_type"] for a in fetch_alerts(settings, "ACC_LIVE")}
    assert "stalled_account" not in types


# ---------------------------------------------------------------------------
# unresolved_objection
# ---------------------------------------------------------------------------


def test_alert_unresolved_objection_fires_without_resolving_activity(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_OBJ", account_name="Objection Account")
    _pin_reference_date(settings, account_id="ACC_OBJ")
    # An email_thread_summary doc that contains the trigger word "concern".
    seed_rag_document(
        settings,
        doc_id="email_thread_summary:ACC_OBJ:thread1",
        account_id="ACC_OBJ",
        doc_type="email_thread_summary",
        title="Email thread: security concern",
        content="The customer raised a security concern that has not been answered.",
        last_source_updated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_OBJ")
    alerts = [a for a in fetch_alerts(settings, "ACC_OBJ") if a["alert_type"] == "unresolved_objection"]
    assert len(alerts) == 1
    assert "email_thread_summary:ACC_OBJ:thread1" in alerts[0]["evidence_doc_ids"]


def test_alert_unresolved_objection_suppressed_when_later_activity_resolves(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_OBJ2", account_name="Objection Account Resolved")
    _pin_reference_date(settings, account_id="ACC_OBJ2")
    seed_rag_document(
        settings,
        doc_id="email_thread_summary:ACC_OBJ2:t",
        account_id="ACC_OBJ2",
        doc_type="email_thread_summary",
        title="Email thread: security concern",
        content="Customer raised a security concern about EU hosting.",
        last_source_updated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    )
    # A later activity that mentions a resolution keyword — should suppress.
    seed_activity(
        settings,
        activity_id="ACT_RESOLVED",
        account_id="ACC_OBJ2",
        activity_date=REFERENCE_DATE - timedelta(days=1),
        subject="Security concern resolved",
        description="The customer concern was addressed in writing.",
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_OBJ2")
    types = {a["alert_type"] for a in fetch_alerts(settings, "ACC_OBJ2")}
    assert "unresolved_objection" not in types


# ---------------------------------------------------------------------------
# missing_followup
# ---------------------------------------------------------------------------


def test_alert_missing_followup_for_overdue_high_priority_task(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_MF", account_name="Missing Followup")
    _pin_reference_date(settings, account_id="ACC_MF")
    seed_activity(
        settings,
        activity_id="ACT_OVERDUE",
        account_id="ACC_MF",
        subject="High priority follow up",
        priority="High",
        status="Open",
        activity_date=REFERENCE_DATE - timedelta(days=10),
    )
    # And a same-day high-priority open task that is *not* overdue.
    seed_activity(
        settings,
        activity_id="ACT_TODAY",
        account_id="ACC_MF",
        subject="Today's task",
        priority="High",
        status="Open",
        activity_date=REFERENCE_DATE,
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_MF")
    alerts = [a for a in fetch_alerts(settings, "ACC_MF") if a["alert_type"] == "missing_followup"]
    assert len(alerts) == 1
    assert "ACT_OVERDUE" in alerts[0]["body_markdown"]


# ---------------------------------------------------------------------------
# champion_positive_signal
# ---------------------------------------------------------------------------


def test_alert_champion_positive_signal_picks_up_recent_phrase(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_GO", account_name="Greenlight Account")
    _pin_reference_date(settings, account_id="ACC_GO")
    seed_rag_document(
        settings,
        doc_id="email_thread_summary:ACC_GO:positive",
        account_id="ACC_GO",
        doc_type="email_thread_summary",
        title="Email thread: pilot greenlight",
        content="The procurement lead said let's move forward with the pilot.",
        last_source_updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=timezone.utc),
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_GO")
    alerts = [a for a in fetch_alerts(settings, "ACC_GO") if a["alert_type"] == "champion_positive_signal"]
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "info"


# ---------------------------------------------------------------------------
# data_inconsistency
# ---------------------------------------------------------------------------


def test_alert_data_inconsistency_when_closed_won_has_no_contract(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_DI", account_name="Data Inconsistency")
    _pin_reference_date(settings, account_id="ACC_DI")
    seed_opportunity(
        settings,
        opportunity_id="OPP_DI",
        account_id="ACC_DI",
        name="Closed-won without contract",
        stage="Closed Won",
        close_date=REFERENCE_DATE - timedelta(days=5),
        is_closed=True,
        is_won=True,
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_DI")
    alerts = [a for a in fetch_alerts(settings, "ACC_DI") if a["alert_type"] == "data_inconsistency"]
    assert len(alerts) == 1
    assert "OPP_DI" in alerts[0]["body_markdown"]


def test_alert_data_inconsistency_suppressed_when_contract_linked(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_OK", account_name="OK Account")
    _pin_reference_date(settings, account_id="ACC_OK")
    seed_opportunity(
        settings,
        opportunity_id="OPP_OK",
        account_id="ACC_OK",
        name="Closed-won with contract",
        stage="Closed Won",
        close_date=REFERENCE_DATE - timedelta(days=5),
        is_closed=True,
        is_won=True,
    )
    seed_contract(
        settings,
        contract_id="CTR_OK",
        account_id="ACC_OK",
        contract_number="OK-001",
        opportunity_id="OPP_OK",
    )

    ProactiveAlertGenerator(settings).generate_for_account("ACC_OK")
    types = {a["alert_type"] for a in fetch_alerts(settings, "ACC_OK")}
    assert "data_inconsistency" not in types


# ---------------------------------------------------------------------------
# Session scoping
# ---------------------------------------------------------------------------


def test_alerts_are_session_scoped(migrated_db: str) -> None:
    """Generating for one session must not pollute another session's row group."""
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_SS", account_name="Session Scope")
    _pin_reference_date(settings, account_id="ACC_SS")
    seed_activity(
        settings, activity_id="ACT_OLD2", account_id="ACC_SS",
        activity_date=REFERENCE_DATE - timedelta(days=30),
    )

    generator = ProactiveAlertGenerator(settings)
    generator.generate_for_account("ACC_SS", session_id="session-a")
    generator.generate_for_account("ACC_SS", session_id="session-b")

    alerts = fetch_alerts(settings, "ACC_SS")
    # Each session has its own stalled_account alert with a session-scoped id.
    session_a_alerts = [a for a in alerts if ":session:" in a["alert_id"]]
    assert len(session_a_alerts) >= 2
    # And running generation for session-a again does not delete session-b's rows.
    generator.generate_for_account("ACC_SS", session_id="session-a")
    alerts_after = fetch_alerts(settings, "ACC_SS")
    assert any(":session:" in a["alert_id"] for a in alerts_after)
