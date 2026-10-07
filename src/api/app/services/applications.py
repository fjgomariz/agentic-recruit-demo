"""Candidate application workflow: validate, store the resume, and record the application."""

import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import PurePath

from app.domain import ApplicationDecision, ApplicationEvaluation, ApplicationReview, Job, JobApplication, JobStatus
from app.repositories import CosmosApplicationRepository
from app.services.crud import CrudService, EntityNotFoundError
from app.storage import ResumeStore

logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024


class _Unset:
    """Marker for 'leave this field unchanged' in partial updates."""


UNSET = _Unset()


class ApplicationNotAllowedError(ValueError):
    """Raised when the job does not accept applications or the submission is invalid."""


def clean_file_name(file_name: str | None) -> str:
    """Keep only the base name and safe characters of the uploaded file name."""

    name = PurePath((file_name or "").replace("\\", "/")).name
    name = re.sub(r"[^\w.\- ()]", "_", name).strip() or "resume.pdf"
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"


class ApplicationService:
    """Coordinate jobs, resume storage, and application records."""

    def __init__(self, jobs: CrudService[Job], applications: CosmosApplicationRepository, resumes: ResumeStore) -> None:
        self._jobs = jobs
        self._applications = applications
        self._resumes = resumes

    async def submit(
        self,
        job_id: str,
        candidate_name: str,
        candidate_email: str,
        message: str,
        file_name: str | None,
        resume: bytes,
    ) -> JobApplication:
        """Store the resume and create the application for a published job."""

        job = await self._jobs.get(job_id)
        if job.status != JobStatus.PUBLISHED:
            raise ApplicationNotAllowedError("This job is not accepting applications")
        if not resume:
            raise ApplicationNotAllowedError("The resume file is empty")
        if len(resume) > MAX_RESUME_BYTES:
            raise ApplicationNotAllowedError("The resume must be 5 MB or smaller")
        if not resume.startswith(b"%PDF-"):
            raise ApplicationNotAllowedError("The resume must be a PDF file")

        application_id = uuid.uuid4().hex
        blob_name = f"{application_id}.pdf"
        application = JobApplication(
            id=application_id,
            job_id=job.id,
            candidate_name=candidate_name.strip(),
            candidate_email=candidate_email.strip(),
            message=message.strip(),
            resume_file_name=clean_file_name(file_name),
            resume_blob_path=f"{self._resumes.container_name}/{blob_name}",
            submitted_at=datetime.now(UTC),
        )

        await self._resumes.upload(blob_name, resume)
        try:
            return await self._applications.create(application)
        except Exception:
            # Do not leave an orphaned resume behind when the record cannot be written.
            logger.exception("Failed to record application id=%s; removing its resume", application_id)
            await self._resumes.delete(blob_name)
            raise

    async def list_for_job(self, job_id: str) -> list[JobApplication]:
        return await self._applications.list_for_job(job_id)

    async def list_all(self) -> list[JobApplication]:
        return await self._applications.list_all()

    async def get(self, application_id: str) -> JobApplication:
        application = await self._applications.get(application_id)
        if application is None:
            raise EntityNotFoundError(f"Application '{application_id}' was not found")
        return application

    async def get_resume(self, application_id: str) -> tuple[JobApplication, bytes]:
        application = await self.get(application_id)
        blob_name = application.resume_blob_path.split("/", 1)[-1]
        return application, await self._resumes.download(blob_name)

    async def get_job(self, job_id: str) -> Job:
        return await self._jobs.get(job_id)

    async def update_assessment(
        self,
        application: JobApplication,
        *,
        evaluation: ApplicationEvaluation | None | _Unset = UNSET,
        review: ApplicationReview | None | _Unset = UNSET,
        decision: ApplicationDecision | None | _Unset = UNSET,
    ) -> JobApplication:
        """Set the given assessment fields in one partial update; omitted fields are left untouched, None clears."""

        fields = {name: value for name, value in (("evaluation", evaluation), ("review", review), ("decision", decision)) if value is not UNSET}
        return await self._applications.set_fields(application, fields)
