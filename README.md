# Agentic Recruiting Foundry Demo

## Vision

Agentic Recruiting Foundry Demo is a business-facing demonstration of Microsoft Foundry. It uses a familiar recruitment scenario to make advanced AI platform capabilities tangible, rather than to prescribe a production recruiting solution.

The demo shows how a governed, observable system of AI agents can support a recruitment journey: creating job descriptions, receiving candidate information, evaluating applications, and preparing recruiter-led decisions. The emphasis is on the platform practices needed to operate agentic applications responsibly at scale.

## Business Scenario

An organization wants to improve the consistency and speed of its early recruitment workflow while keeping people accountable for consequential decisions. Candidates interact with a public portal to discover opportunities and submit their information. Recruiters use an administration portal to author jobs, inspect candidate assessments, and approve or reject agent-proposed next steps.

Behind those experiences, specialized agents collaborate on distinct tasks:

- A **job authoring agent** helps create clear, role-specific job descriptions.
- A **candidate evaluation agent** assesses candidate materials against the defined role criteria.
- A **candidate review agent** synthesizes findings into a recruiter-friendly review.

Candidate and job data are represented in Cosmos DB, with supporting documents held in Azure Blob Storage. These services provide the scenario context for demonstrating an end-to-end agentic application without making recruitment automation itself the objective.

## Architecture Vision

The application is organized around two human experiences and a coordinated agent layer:

| Area | Purpose |
| --- | --- |
| Public candidate portal | Candidate-facing entry point for exploring roles and supplying application information. |
| Recruiter administration portal | Recruiter workspace for job management, candidate review, and human approvals. |
| Agent collaboration | A set of focused agents that exchange context and produce traceable outputs for the recruitment workflow. |
| Business data and documents | Cosmos DB and Azure Blob Storage supply durable scenario data and candidate materials. |
| Foundry operations layer | Shared capabilities for observing, evaluating, monitoring, governing, and comparing the agentic system. |

Human approval is a central architectural boundary. Agents can prepare recommendations and supporting evidence, while recruiters retain control over decisions and workflow progression.

## Development and deployment

Application-specific local setup is documented under each application folder. Continuous validation, GitHub OIDC setup, and the update-only development deployment process are documented in [docs/deployment.md](docs/deployment.md).

## Foundry Learning Objectives

The demo is designed to explore the following Microsoft Foundry capabilities:

- **Agent Service** — build and operate agents as managed application components.
- **Multi-agent orchestration** — coordinate specialized agents across a business workflow.
- **Observability** — understand agent behavior, interactions, and outcomes through traceability.
- **Evaluations** — assess response quality and workflow performance against defined criteria.
- **Monitoring** — maintain visibility into the health and behavior of the running system.
- **Cost analysis** — identify how agent usage contributes to operational cost.
- **Model comparison** — compare models against scenario-specific quality, latency, and cost considerations.
- **Human approval workflows** — keep accountable users in control of important decisions.
- **Governance** — apply appropriate controls, reviewability, and responsible AI practices to an agentic application.

## What This Demo Is—and Is Not

This is a learning environment for demonstrating Foundry capabilities through a concrete business scenario. It is not intended to automate hiring decisions, replace recruiter judgment, or define a complete recruitment platform. The recruitment setting exists to show how agentic systems can be composed, measured, governed, and improved while people remain responsible for outcomes.
