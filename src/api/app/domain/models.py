"""Pydantic representations of the canonical shared recruitment domain."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

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


class JobDescriptionRequest(DomainModel):
    """Role facts and recruiter notes sent to the job description agent."""

    title: str = Field(min_length=1, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    workplace_type: WorkplaceType | None = None
    employment_type: EmploymentType | None = None
    experience_level: ExperienceLevel | None = None
    hiring_manager: str | None = Field(default=None, max_length=120)
    notes: str = Field(default="", max_length=4000)


class JobDescriptionDraft(DomainModel):
    """Candidate-facing content proposed by the job description agent."""

    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), populate_by_name=True, extra="forbid")

    summary: str
    description: str
    responsibilities: list[str]
    qualifications: list[str]
    preferred_qualifications: list[str]


class JobDescriptionDraftResult(DomainModel):
    """Agent draft plus the traceable identifiers of the agent run that produced it."""

    draft: JobDescriptionDraft
    execution_id: str
    agent_name: str
    agent_version: str | None = None


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
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class EvaluationRecommendation(StrEnum):
    """Advisory outcome proposed by the candidate evaluation agent."""

    STRONG_MATCH = "Strong match"
    POSSIBLE_MATCH = "Possible match"
    NOT_A_MATCH = "Not a match"
    NEEDS_MANUAL_REVIEW = "Needs manual review"


class ApplicationEvaluation(DomainModel):
    """AI evaluation of an application, embedded in the application document."""

    status: EvaluationStatus
    started_at: datetime
    completed_at: datetime | None = None
    agent_name: str
    agent_version: str | None = None
    agent_execution_id: str | None = None
    model: str | None = None
    overall_score: int | None = Field(default=None, ge=0, le=100)
    recommendation: EvaluationRecommendation | None = None
    summary: str | None = None
    strengths: list[str] = Field(default_factory=list)
    considerations: list[str] = Field(default_factory=list)
    scores: list[EvaluationScore] = Field(default_factory=list)
    error_message: str | None = None


class ReviewAgreement(StrEnum):
    """How far the reviewer agrees with the evaluator."""

    AGREES = "Agrees"
    PARTIALLY_AGREES = "Partially agrees"
    DISAGREES = "Disagrees"


class ReviewConfidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ReviewFindingType(StrEnum):
    UNSUPPORTED_CLAIM = "Unsupported claim"
    MISSED_EVIDENCE = "Missed evidence"
    SCORE_MISMATCH = "Score mismatch"
    POTENTIAL_BIAS = "Potential bias"
    OVERCONFIDENCE = "Overconfidence"


class ReviewFindingSeverity(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReviewFinding(DomainModel):
    """One inconsistency the reviewer found in the evaluation."""

    type: ReviewFindingType
    severity: ReviewFindingSeverity
    description: str


class ApplicationReview(DomainModel):
    """Checker-agent review of the evaluation, embedded in the application document."""

    status: EvaluationStatus
    started_at: datetime
    completed_at: datetime | None = None
    agent_name: str
    agent_version: str | None = None
    agent_execution_id: str | None = None
    model: str | None = None
    reviewed_evaluation_id: str | None = None
    original_score: int | None = Field(default=None, ge=0, le=100)
    validated_score: int | None = Field(default=None, ge=0, le=100)
    final_recommendation: EvaluationRecommendation | None = None
    agreement: ReviewAgreement | None = None
    confidence: ReviewConfidence | None = None
    summary: str | None = None
    comments: list[str] = Field(default_factory=list)
    inconsistencies: list[ReviewFinding] = Field(default_factory=list)
    error_message: str | None = None


AiAssessmentRating = Literal["Accurate", "Partially accurate", "Inaccurate"]


class ApplicationDecision(DomainModel):
    """Recruiter approval: the final decision plus a snapshot of the AI advice it was based on."""

    status: Literal["Advanced", "Rejected"]
    comment: str = Field(default="", max_length=1000)
    decided_by: str = Field(default="Recruiter", min_length=1, max_length=120)
    decided_at: datetime
    ai_rating: AiAssessmentRating | None = None
    agent_feedback: str = Field(default="", max_length=2000)
    ai_recommendation: EvaluationRecommendation | None = None
    ai_score: int | None = Field(default=None, ge=0, le=100)
    followed_ai: bool | None = None
    evaluation_execution_id: str | None = None
    review_execution_id: str | None = None


class ApplicationDecisionRequest(DomainModel):
    """Recruiter input to record a decision."""

    status: Literal["Advanced", "Rejected"]
    comment: str = Field(default="", max_length=1000)
    decided_by: str = Field(default="Recruiter", min_length=1, max_length=120)
    ai_rating: AiAssessmentRating | None = None
    agent_feedback: str = Field(default="", max_length=2000)


class AgentFeedback(DomainModel):
    """Recruiter feedback on the AI workflow for one decision, without candidate personal data."""

    application_id: str
    job_id: str
    decided_at: datetime
    decision: Literal["Advanced", "Rejected"]
    ai_recommendation: EvaluationRecommendation | None = None
    followed_ai: bool | None = None
    ai_rating: AiAssessmentRating | None = None
    agent_feedback: str = ""
    evaluation_score: int | None = None
    validated_score: int | None = None
    reviewer_agreement: ReviewAgreement | None = None
    evaluator_version: str | None = None
    reviewer_version: str | None = None


class JobApplication(DomainModel):
    """Candidate application to one job, with the resume stored in Blob Storage."""

    id: str
    job_id: str
    candidate_name: str = Field(min_length=1, max_length=120)
    candidate_email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    message: str = Field(default="", max_length=2000)
    resume_file_name: str
    resume_blob_path: str
    submitted_at: datetime
    evaluation: ApplicationEvaluation | None = None
    review: ApplicationReview | None = None
    decision: ApplicationDecision | None = None