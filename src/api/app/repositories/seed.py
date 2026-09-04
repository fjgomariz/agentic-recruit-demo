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
        Job.model_validate({**common, "id": "revenue-operations-analyst", "title": "Revenue Operations Analyst", "department": "Operations", "location": {"displayName": "Dublin, IE", "workplaceType": "Hybrid", "countryCode": "IE"}, "status": "Draft", "experienceLevel": "Mid", "summary": "Turn revenue data into trusted operating insights.", "description": "Turn revenue data into trusted operating insights for go-to-market teams.", "responsibilities": ["Analyze revenue performance.", "Improve reporting workflows."], "qualifications": ["Advanced spreadsheet and CRM skills", "Analytical problem solving"], "hiringManager": "Elena Rossi"}),
        Job.model_validate({**common, "id": "ai-solutions-engineer", "title": "AI Solutions Engineer", "department": "Engineering", "location": {"displayName": "New York, NY", "workplaceType": "Hybrid", "countryCode": "US"}, "status": "Published", "experienceLevel": "Senior", "summary": "Build reliable AI-powered product experiences and help establish the engineering patterns behind them.", "description": "Build customer-facing AI capabilities and the systems that make them dependable, observable, and measurable.", "responsibilities": ["Build and maintain AI-assisted application features.", "Design evaluation, tracing, and quality-monitoring workflows."], "qualifications": ["4+ years of software engineering experience.", "Proficiency in Python or TypeScript."], "preferredQualifications": ["Experience with Azure AI Foundry."], "hiringManager": "Daniel Kim", "publishedAt": "2026-08-31T09:00:00Z", "applicantCount": 16, "featured": True}),
        Job.model_validate({**common, "id": "product-marketing-manager", "title": "Product Marketing Manager", "department": "Marketing", "location": {"displayName": "San Francisco, CA", "workplaceType": "Hybrid", "countryCode": "US"}, "status": "Published", "experienceLevel": "Senior", "summary": "Define compelling product narratives and help teams bring new capabilities to market.", "description": "Connect customer insight, product strategy, and go-to-market execution.", "responsibilities": ["Own positioning and messaging.", "Plan cross-functional launches."], "qualifications": ["4+ years in product marketing.", "Strong writing and analytical skills."], "preferredQualifications": ["Enterprise technology experience."], "hiringManager": "Priya Shah", "publishedAt": "2026-08-27T09:00:00Z", "applicantCount": 19}),
        Job.model_validate({**common, "id": "frontend-engineer", "title": "Frontend Engineer", "department": "Engineering", "location": {"displayName": "Austin, TX", "workplaceType": "Remote", "countryCode": "US"}, "status": "Published", "experienceLevel": "Mid", "summary": "Create fast, accessible interfaces that make sophisticated technology feel effortless.", "description": "Build component systems and product surfaces used by customers every day.", "responsibilities": ["Build accessible React experiences.", "Improve frontend performance."], "qualifications": ["3+ years with React and TypeScript.", "Knowledge of web accessibility."], "preferredQualifications": ["Next.js experience."], "hiringManager": "Daniel Kim", "publishedAt": "2026-08-26T09:00:00Z", "applicantCount": 31}),
        Job.model_validate({**common, "id": "design-researcher", "title": "Design Researcher", "department": "Product & Design", "location": {"displayName": "London, UK", "workplaceType": "Hybrid", "countryCode": "GB"}, "status": "Published", "employmentType": "Contract", "experienceLevel": "Mid", "summary": "Turn customer needs and behaviors into insights that guide responsible product decisions.", "description": "Plan and conduct research across emerging product experiences.", "responsibilities": ["Plan mixed-method research studies.", "Synthesize findings into opportunities."], "qualifications": ["3+ years conducting product research.", "Strong interviewing and synthesis skills."], "preferredQualifications": ["Knowledge of inclusive research practices."], "hiringManager": "Maya Patel", "publishedAt": "2026-08-20T09:00:00Z", "applicantCount": 12}),
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