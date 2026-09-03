"""Pydantic representations of the canonical shared recruitment domain."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    """Base model using the camelCase contract shared with the portals."""

    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), populate_by_name=True)


def _to_camel(value: str) -> str:
    """Convert a snake_case Python field name to the shared camelCase shape."""

    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class JobStatus(StrEnum):
    """Lifecycle state of a job posting."""

    DRAFT = "Draft"
    PENDING_APPROVAL = "Pending Approval"
    PUBLISHED = "Published"
    CLOSED = "Closed"


class WorkplaceType(StrEnum):
    """Supported work arrangement."""

    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"


class EmploymentType(StrEnum):
    """Contractual employment arrangement."""

    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"


class ExperienceLevel(StrEnum):
    """Expected career level for a job."""

    ENTRY = "Entry"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"
    EXECUTIVE = "Executive"


class JobLocation(DomainModel):
    """Structured location and work arrangement for a job."""

    display_name: str
    workplace_type: WorkplaceType
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class Job(DomainModel):
    """Canonical job posting."""

    id: str
    title: str
    department: str
    location: JobLocation
    status: JobStatus
    employment_type: EmploymentType
    experience_level: ExperienceLevel
    summary: str
    description: str
    responsibilities: list[str]
    qualifications: list[str]
    preferred_qualifications: list[str]
    hiring_manager: str
    created_at: datetime
    published_at: datetime | None = None
    applicant_count: int = Field(ge=0)
    featured: bool | None = None
    authoring_execution_id: str | None = None


class ApplicationStage(StrEnum):
    """Current workflow stage of an application."""

    AI_REVIEW = "AI review"
    RECRUITER_REVIEW = "Recruiter review"
    HIRING_MANAGER_REVIEW = "Hiring manager review"
    CLOSED = "Closed"


class ApplicationStatus(StrEnum):
    """Lifecycle state of an application."""

    SUBMITTED = "Submitted"
    IN_REVIEW = "In review"
    ADVANCED = "Advanced"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"


class Candidate(DomainModel):
    """Person who may submit applications to jobs."""

    id: str
    first_name: str
    last_name: str
    email: str
    location: str
    profile_url: str | None = None


class Resume(DomainModel):
    """Resume metadata owned by a candidate."""

    id: str
    candidate_id: str
    file_name: str
    content_type: str
    storage_reference: str
    summary: str | None = None
    uploaded_at: datetime


class CandidateApplication(DomainModel):
    """Candidate submission for one job."""

    id: str
    candidate_id: str
    job_id: str
    resume_id: str
    stage: ApplicationStage
    status: ApplicationStatus
    interest_statement: str | None = None
    applied_at: datetime
    evaluation_id: str | None = None


class EvaluationStatus(StrEnum):
    """Lifecycle state of a candidate evaluation."""

    COMPLETED = "Completed"
    IN_PROGRESS = "In progress"
    NEEDS_REVIEW = "Needs review"
    FAILED = "Failed"


class EvaluationScore(DomainModel):
    """One normalized scoring dimension in an evaluation report."""

    id: str
    criterion: str
    value: float = Field(ge=0)
    maximum_value: float = Field(gt=0)
    rationale: str | None = None


class EvaluationReport(DomainModel):
    """Recruiter-readable report produced by an evaluation."""

    id: str
    evaluation_id: str
    overall_score: float = Field(ge=0, le=100)
    summary: str
    strengths: list[str]
    considerations: list[str]
    recommendation: str
    scores: list[EvaluationScore]
    generated_at: datetime


class CandidateEvaluation(DomainModel):
    """Evaluation of one application against its job criteria."""

    id: str
    application_id: str
    status: EvaluationStatus
    agent_execution_id: str
    report_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class ApprovalStatus(StrEnum):
    """Lifecycle state of a human approval workflow."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CHANGES_REQUESTED = "Changes Requested"


class ApprovalTargetType(StrEnum):
    """Entity types that can require human approval."""

    JOB = "Job"
    CANDIDATE_APPLICATION = "CandidateApplication"


class ApprovalWorkflow(DomainModel):
    """Human decision checkpoint for a consequential workflow."""

    id: str
    target_type: ApprovalTargetType
    target_id: str
    status: ApprovalStatus
    requested_by: str
    requested_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    comment: str | None = None
    agent_execution_id: str | None = None


class AgentExecutionStatus(StrEnum):
    """Runtime state of an agent execution."""

    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    NEEDS_REVIEW = "Needs review"


class AgentExecution(DomainModel):
    """Observable record of one agent invocation."""

    id: str
    agent_name: str
    model: str
    status: AgentExecutionStatus
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    configuration_version: str
    related_entity_ids: list[str]
    output_summary: str | None = None
    error_message: str | None = None