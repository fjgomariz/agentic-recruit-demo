"""Seed records transcribed from the shared TypeScript mock data."""

from app.domain import Candidate, CandidateEvaluation, Job


def create_seed_jobs() -> list[Job]:
    """Create representative jobs shared by the candidate and recruiter portals."""

    common = {
        "employmentType": "Full-time",
        "preferredQualifications": [],
        "createdAt": "2026-09-01T09:00:00Z",
        "applicantCount": 0,
    }
    return [
        Job.model_validate({**common, "id": "senior-product-designer", "title": "Senior Product Designer", "department": "Product & Design", "location": {"displayName": "London, UK", "workplaceType": "Hybrid", "countryCode": "GB"}, "status": "Published", "experienceLevel": "Senior", "summary": "Shape intuitive, human-centered experiences for intelligent workplace tools.", "description": "Lead end-to-end product design for our recruiter intelligence experience.", "responsibilities": ["Lead product design from discovery through delivery."], "qualifications": ["6+ years of product design experience"], "hiringManager": "Maya Patel", "publishedAt": "2026-09-01T09:00:00Z", "applicantCount": 42, "featured": True, "authoringExecutionId": "run_84f29"}),
        Job.model_validate({**common, "id": "ai-platform-engineer", "title": "AI Platform Engineer", "department": "Engineering", "location": {"displayName": "Remote - UK", "workplaceType": "Remote", "countryCode": "GB"}, "status": "Pending Approval", "experienceLevel": "Senior", "summary": "Build reliable platform capabilities for responsible AI-powered products.", "description": "Help product teams safely integrate Azure AI services into customer workflows.", "responsibilities": ["Build AI platform integrations."], "qualifications": ["Python and cloud platform experience"], "preferredQualifications": ["Experience with Azure AI Foundry."], "hiringManager": "Daniel Kim", "authoringExecutionId": "run_84f29"}),
        Job.model_validate({**common, "id": "customer-success-manager", "title": "Customer Success Manager", "department": "Customer Experience", "location": {"displayName": "New York, US", "workplaceType": "Hybrid", "countryCode": "US"}, "status": "Published", "experienceLevel": "Senior", "summary": "Help strategic customers realize value and build durable partnerships.", "description": "Guide strategic customers to measurable outcomes.", "responsibilities": ["Create measurable customer success plans."], "qualifications": ["5+ years in B2B customer success"], "hiringManager": "Avery Johnson", "publishedAt": "2026-08-22T09:00:00Z", "applicantCount": 28}),
    ]


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