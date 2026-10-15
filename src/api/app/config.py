"""Environment-backed application configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CosmosSettings:
    """Connection settings for the recruitment Cosmos DB account."""

    endpoint: str
    database_name: str = "recruitment"
    jobs_container_name: str = "jobs"
    applications_container_name: str = "applications"
    agent_executions_container_name: str = "agent-executions"
    key: str | None = None

    @classmethod
    def from_environment(cls) -> "CosmosSettings":
        """Load Cosmos DB settings from process environment variables."""

        endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
        if not endpoint:
            raise RuntimeError("AZURE_COSMOS_ENDPOINT must be configured")
        return cls(
            endpoint=endpoint,
            database_name=os.getenv("AZURE_COSMOS_DATABASE_NAME", "recruitment"),
            jobs_container_name=os.getenv("AZURE_COSMOS_JOBS_CONTAINER_NAME", "jobs"),
            applications_container_name=os.getenv("AZURE_COSMOS_APPLICATIONS_CONTAINER_NAME", "applications"),
            agent_executions_container_name=os.getenv("AZURE_COSMOS_AGENT_EXECUTIONS_CONTAINER_NAME", "agent-executions"),
            key=os.getenv("AZURE_COSMOS_KEY"),
        )


@dataclass(frozen=True)
class StorageSettings:
    """Blob Storage settings for uploaded resumes."""

    blob_endpoint: str | None
    resumes_container_name: str = "resumes"

    @classmethod
    def from_environment(cls) -> "StorageSettings":
        """Load storage settings; a missing endpoint disables resume upload instead of failing startup."""

        return cls(
            blob_endpoint=os.getenv("AZURE_STORAGE_BLOB_ENDPOINT") or None,
            resumes_container_name=os.getenv("AZURE_STORAGE_RESUMES_CONTAINER_NAME", "resumes"),
        )


@dataclass(frozen=True)
class AgentSettings:
    """Connection settings for the Foundry project that hosts the recruitment agents."""

    project_endpoint: str | None
    job_description_agent_name: str = "job-description-writer"
    candidate_evaluation_agent_name: str = "candidate-evaluator"
    candidate_review_agent_name: str = "candidate-evaluation-reviewer"
    recruiter_copilot_agent_name: str = "recruiter-copilot"
    model_deployment_name: str = "gpt-5.4-mini"
    review_model_deployment_name: str = "gpt-5.4"

    @classmethod
    def from_environment(cls) -> "AgentSettings":
        """Load agent settings; a missing endpoint disables AI features instead of failing startup."""

        return cls(
            project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or None,
            job_description_agent_name=os.getenv("JOB_DESCRIPTION_AGENT_NAME", "job-description-writer"),
            candidate_evaluation_agent_name=os.getenv("CANDIDATE_EVALUATION_AGENT_NAME", "candidate-evaluator"),
            candidate_review_agent_name=os.getenv("CANDIDATE_REVIEW_AGENT_NAME", "candidate-evaluation-reviewer"),
            recruiter_copilot_agent_name=os.getenv("RECRUITER_COPILOT_AGENT_NAME", "recruiter-copilot"),
            model_deployment_name=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini"),
        )


@dataclass(frozen=True)
class KnowledgeSettings:
    """Foundry IQ knowledge base (Azure AI Search) and the private containers its documents come from."""

    search_endpoint: str | None
    knowledge_base_name: str = "recruiting-iq"
    talent_pool_container_name: str = "talent-pool"
    hiring_policies_container_name: str = "hiring-policies"

    @classmethod
    def from_environment(cls) -> "KnowledgeSettings":
        """Load knowledge settings; a missing Search endpoint disables the talent pool instead of failing startup."""

        return cls(
            search_endpoint=(os.getenv("AZURE_SEARCH_ENDPOINT") or "").rstrip("/") or None,
            knowledge_base_name=os.getenv("KNOWLEDGE_BASE_NAME", "recruiting-iq"),
            talent_pool_container_name=os.getenv("AZURE_STORAGE_TALENT_POOL_CONTAINER_NAME", "talent-pool"),
            hiring_policies_container_name=os.getenv("AZURE_STORAGE_HIRING_POLICIES_CONTAINER_NAME", "hiring-policies"),
        )