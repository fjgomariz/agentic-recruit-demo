"""Seed records for entities that are not yet persisted in Cosmos DB."""

from app.domain import Candidate, CandidateEvaluation


def create_seed_candidates() -> list[Candidate]:
    """Create candidates matching the shared recruiting mock data."""

    return [
        Candidate(id="olivia-bennett", first_name="Olivia", last_name="Bennett", email="olivia.bennett@example.demo", location="London, UK", profile_url="https://example.demo/olivia-bennett"),
        Candidate(id="marcus-chen", first_name="Marcus", last_name="Chen", email="marcus.chen@example.demo", location="Manchester, UK"),
        Candidate(id="sofia-martin", first_name="Sofia", last_name="Martin", email="sofia.martin@example.demo", location="Paris, FR"),
        Candidate(id="james-wilson", first_name="James", last_name="Wilson", email="james.wilson@example.demo", location="Brooklyn, US"),
    ]


def create_seed_evaluations() -> list[CandidateEvaluation]:
    """Create candidate evaluations matching shared application identifiers."""

    return [
        CandidateEvaluation(id="evaluation-olivia-bennett", application_id="application-olivia-bennett", status="Completed", agent_execution_id="run_84f2a", report_id="report-olivia-bennett", started_at="2026-09-02T09:00:10Z", completed_at="2026-09-02T09:00:24Z"),
        CandidateEvaluation(id="evaluation-marcus-chen", application_id="application-marcus-chen", status="Completed", agent_execution_id="run_84f2a", report_id="report-marcus-chen", started_at="2026-09-02T09:00:10Z", completed_at="2026-09-02T09:00:24Z"),
        CandidateEvaluation(id="evaluation-sofia-martin", application_id="application-sofia-martin", status="Needs review", agent_execution_id="run_84f21", report_id="report-sofia-martin", started_at="2026-09-02T09:00:10Z"),
        CandidateEvaluation(id="evaluation-james-wilson", application_id="application-james-wilson", status="Completed", agent_execution_id="run_84f2a", report_id="report-james-wilson", started_at="2026-09-02T09:00:10Z", completed_at="2026-09-02T09:00:24Z"),
    ]
