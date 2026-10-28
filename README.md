# Agentic Recruiting Foundry Demo

## Vision

Agentic Recruiting Foundry Demo is a business-facing demonstration of Microsoft Foundry. It uses a familiar recruitment scenario to make advanced AI platform capabilities tangible, rather than to prescribe a production recruiting solution.

The demo shows how a governed, observable system of AI agents can support a recruitment journey: creating job descriptions, receiving candidate information, evaluating applications, and preparing recruiter-led decisions. The emphasis is on the platform practices needed to operate agentic applications responsibly at scale.

## Business Scenario

An organization wants to improve the consistency and speed of its early recruitment workflow while keeping people accountable for consequential decisions. Candidates interact with a public portal to discover opportunities and submit their information. Recruiters use an administration portal to author jobs, inspect candidate assessments, and approve or reject agent-proposed next steps.

Behind those experiences, specialized agents collaborate on distinct tasks:

- A **job description writer** drafts clear, role-specific job postings from a recruiter's notes.
- A **candidate evaluator** (the maker) scores each resume against the role and cites evidence.
- A **candidate evaluation reviewer** (the checker, on a different model) verifies that evaluation and flags unsupported claims, bias and overconfidence.
- A **recruiter copilot** uses **Foundry IQ** (agentic retrieval over an Azure AI Search knowledge base) to find past candidates in a talent pool and check them against hiring policies, citing every source.

Candidate and job data are represented in Cosmos DB, with supporting documents held in Azure Blob Storage. These services provide the scenario context for demonstrating an end-to-end agentic application without making recruitment automation itself the objective.

## Run your own copy

The demo deploys into your own Azure subscription from GitHub Actions, in about 30 minutes:

1. Fork the repository and sign in with `az login` and `gh auth login`.
2. Run `./infra/scripts/bootstrap.ps1` once. It prepares the subscription (providers, quota check, a least-privilege deployment identity) and the GitHub environment.
3. Run the **Deploy development** workflow and make the three container packages public.
4. Run `./infra/scripts/setup-auth.ps1` to add Microsoft Entra sign-in, then deploy again.
5. Open the portals from the workflow summary and try the synthetic jobs and resumes in [samples/applicants](samples/applicants/README.md).

You need an Azure subscription where you can assign roles, model quota for the gpt-5.4 family, and a lab or demo tenant (not a Microsoft corporate tenant). Expect roughly **$125 to $200 a month** while it is deployed; see [Cost and tear down](docs/deployment.md#cost) before you start. The full guide, with prerequisites and troubleshooting, is [docs/deployment.md](docs/deployment.md).

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

Application-specific local setup is documented under each application folder. The deployment guide, GitHub OIDC setup, cost, teardown and troubleshooting are in [docs/deployment.md](docs/deployment.md); the architecture is in [docs/architecture.md](docs/architecture.md); the agents, their evaluations and Foundry IQ are in [agents/README.md](agents/README.md).

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
