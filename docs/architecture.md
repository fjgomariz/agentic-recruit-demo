# Architecture

## Project Vision

Agentic Recruiting Foundry Demo is a business-facing demonstration platform for Azure AI Foundry. It uses a familiar recruiting workflow to make the design and operation of agentic applications concrete: authoring job descriptions, reviewing candidate information, evaluating applications, and preparing recruiter-led decisions.

The project is not intended to be a production applicant tracking system or an autonomous hiring solution. Its purpose is to demonstrate how organizations can build AI-assisted workflows that are measurable, observable, governable, and cost-aware while keeping people accountable for consequential decisions.

The platform should make the following Azure AI Foundry capabilities visible and easy to explore:

- Managed agents and multi-agent collaboration.
- Repeatable quality and safety evaluations.
- End-to-end tracing, monitoring, and operational diagnostics.
- Human approval and governance controls.
- Model, token, latency, and cost analysis.
- Comparison of agent and model configurations using scenario-specific evidence.

## Architecture Goals

1. **Tell a clear end-to-end story.** A user should be able to follow a request from either portal through agent execution, data access, evaluation, and operational telemetry.
2. **Show platform capabilities explicitly.** Evaluations, traces, policy decisions, and cost data are first-class demo experiences rather than hidden implementation details.
3. **Keep consequential decisions human-owned.** Agents prepare recommendations and evidence; recruiters approve workflow progression and remain responsible for outcomes.
4. **Support safe experimentation.** Models, prompts, tools, and orchestration strategies can be changed and compared without rewriting the business workflow.
5. **Remain understandable.** The architecture favors a small number of explicit components and production-like patterns over unnecessary scale or abstraction.

## Non-Goals

- Replacing recruiter judgment or making autonomous hiring decisions.
- Providing a complete applicant tracking, identity, or HR management system.
- Optimizing for internet-scale throughput or multi-region availability.
- Capturing real candidate data in the demo environment.
- Building custom infrastructure where an Azure managed service demonstrates the intended capability.

## System Context

The platform has two user-facing applications and a shared backend:

| Component | Responsibility |
| --- | --- |
| Public portal | Allows candidates to browse roles and submit demo application information and documents. |
| Recruiter portal | Allows recruiters to author jobs, inspect evidence and assessments, review agent activity, and approve or reject proposed actions. |
| FastAPI service | Owns application APIs, workflow boundaries, authorization checks, persistence, and integration with agents and Azure services. |
| Azure AI Foundry Agent Service | Hosts specialized agents, tool definitions, model configuration, and coordinated agent execution. |
| Evaluation layer | Runs repeatable quality, groundedness, safety, and workflow evaluations against versioned datasets. |
| Operational layer | Correlates requests, agent runs, tool calls, evaluations, latency, token usage, and estimated cost. |
| Data layer | Stores structured scenario data in Azure Cosmos DB and documents in Azure Blob Storage. |

The main business flow is:

1. A recruiter creates or refines a role with assistance from a job-authoring agent.
2. A candidate submits demo profile information and supporting documents through the public portal.
3. A candidate-evaluation agent compares the supplied evidence with explicit role criteria.
4. A candidate-review agent synthesizes the findings, uncertainty, and supporting evidence.
5. A recruiter reviews the traceable recommendation and decides whether the workflow should proceed.
6. Evaluation, telemetry, governance, and cost records make the run inspectable and comparable.

## Repository Architecture

The monorepo is organized by deployable experience and cross-cutting capability:

```text
src/
	public-portal/     Candidate-facing Next.js application
	recruiter-portal/  Recruiter-facing Next.js application
	api/               FastAPI application and business workflows
	agents/            Agent definitions, prompts, tools, and orchestration
	evaluations/       Evaluation datasets, runners, and scoring criteria
	shared/            Shared contracts, models, and utilities
```

Business workflows belong in the API layer. Agent prompts and orchestration belong in the agent layer, while evaluation logic remains independent of both so that it can test the system from the outside. Shared contracts prevent the portals, API, agents, and evaluations from developing incompatible representations of the same concepts.

## Architecture Principles

### 1. Human authority at consequential boundaries

Agent output is advisory. Any action that changes a candidate's status or advances a hiring workflow requires an explicit recruiter decision. The system records the recommendation, evidence, uncertainty, reviewer decision, and relevant versions so the outcome can be reviewed later.

### 2. Specialized agents with explicit contracts

Each agent has one clear responsibility, a defined input and output schema, and a limited tool set. Agents exchange structured artifacts rather than relying on hidden conversational state. This keeps collaboration understandable and allows individual agents to be evaluated or replaced independently.

### 3. Prompts and configuration are versioned assets

Prompts, model settings, tool definitions, policies, and evaluation criteria are stored outside business logic and carry identifiable versions. Every run records the configuration used, enabling reproducibility and meaningful comparison across changes.

### 4. Observability is part of the execution path

Every request receives a correlation identifier that follows it through the API, agent runs, model calls, tool calls, data access, evaluations, and approval events. Logs and traces capture timing, status, model identity, token usage, and errors while excluding unnecessary personal or document content.

### 5. Evaluation precedes promotion

Changes to prompts, agents, models, or orchestration are tested against versioned scenario datasets before becoming the demo default. Evaluation should cover task quality, groundedness, safety, consistency, tool use, latency, and cost. Automated scores are supplemented by human review for subjective or consequential behavior.

### 6. Governance is enforceable and visible

Access control, data handling, content safety, audit records, and human approvals are implemented as system boundaries rather than prompt-only instructions. The recruiter experience should expose why an agent produced a recommendation, what evidence it used, and which policies or approvals affected the workflow.

### 7. Minimize and isolate data

The demo uses synthetic or approved sample data. Structured records and uploaded documents are separated, access is scoped by component, and sensitive content is not copied into logs or evaluation results. Retention and deletion behavior should be explicit and demonstrable.

### 8. Cost is an architectural signal

Token usage, model choice, retries, tool calls, latency, and estimated cost are captured per agent run and aggregated per workflow. Quality, performance, and cost are compared together; the least expensive model is not preferred when it fails the scenario's quality or safety threshold.

### 9. Managed services behind replaceable adapters

The platform uses Azure AI Foundry, Cosmos DB, and Blob Storage directly enough to demonstrate their value, but application code depends on narrow interfaces for model execution, persistence, and file access. This makes tests deterministic and allows demo configurations to evolve without spreading provider details throughout the codebase.

### 10. Simple, production-like implementation

The project favors explicit flows, typed contracts, dependency injection at external boundaries, and small independently testable modules. It avoids speculative abstractions and distributed components that do not improve the learning experience. Reliability features such as validation, timeouts, bounded retries, idempotency, and actionable errors are included where they clarify good practice.

## Cross-Cutting Design

### Agent lifecycle

An agent run is treated as a durable, inspectable unit with:

- The initiating user and workflow context.
- Input and output references.
- Agent, prompt, model, and tool versions.
- Tool-call and handoff events.
- Safety and governance outcomes.
- Evaluation scores where applicable.
- Latency, token usage, and estimated cost.
- Final human disposition for approval-gated workflows.

### Evaluation strategy

Evaluation operates at three levels:

- **Component evaluation:** tests one agent or tool against focused examples.
- **Workflow evaluation:** tests collaboration, handoffs, evidence preservation, and final output quality.
- **Operational evaluation:** compares quality, latency, reliability, and cost across model or configuration variants.

Evaluation datasets must be synthetic, versioned, representative of expected and adversarial conditions, and separated from runtime data.

### Security and governance

The API is the trust boundary for user actions and data access. Portals do not call data stores or agents directly. Managed identities and least-privilege roles are preferred for service-to-service access. Secrets remain in managed configuration, uploaded documents use restricted access, and audit events are append-oriented and correlated with the originating run.

### Failure handling

Agent and model failures must not silently advance the workflow. External calls use timeouts and bounded retries, operations that can be repeated are idempotent, and partial failures produce a visible status that a recruiter can inspect or retry. Human approval remains valid only for the exact recommendation and evidence version reviewed.

## Architectural Success Criteria

The architecture is successful when the demo can:

- Trace a user request across portals, API operations, agents, tools, and data stores.
- Explain an agent recommendation using preserved evidence and version metadata.
- Prevent an agent from independently making or applying a hiring decision.
- Run repeatable evaluations before and after a model, prompt, or orchestration change.
- Compare configurations using quality, safety, latency, token, and cost measures.
- Demonstrate access controls, auditability, and safe data handling without obscuring the business story.
- Replace a model or agent implementation without changing the portals or core domain workflow.

These criteria keep the project focused on its primary purpose: demonstrating how Azure AI Foundry supports agentic applications that can be understood, measured, governed, and improved.
