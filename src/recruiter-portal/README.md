# Recruiter portal

The recruiter portal manages Jobs end to end through the Recruitment Foundry backend API, which stores them in Cosmos DB, and reviews the applications candidates submit on the careers site. Every page reads real data from the API; there is no mock data. Each application goes through a multi-agent assessment (evaluator, then reviewer on a different model) followed by a human approval step.

## Screens and API calls

| Screen | API call |
| --- | --- |
| Overview (metrics, open positions, candidates awaiting your approval) | `GET /jobs`, `GET /applications` |
| Jobs list | `GET /jobs`, `GET /applications` (per-job application counts) |
| Job details, approval review | `GET /jobs/{id}` |
| Create job (`/jobs/new`) | `POST /jobs` with status `Draft` or `Pending Approval` |
| Edit job (`/jobs/{id}/edit`) | `PUT /jobs/{id}`; lifecycle state is unchanged |
| Generate with AI (create and edit) | `POST /job-description-drafts`, which runs the Foundry `job-description-writer` agent |
| Job details (recent applications), Applications (`/jobs/{id}/applications`) | `GET /jobs/{id}/applications` |
| Candidates (`/candidates`): best validated match first, search, job and status filters | `GET /applications`, `GET /jobs` |
| Candidate details (`/candidates/{applicationId}`): workflow, both AI reports, approval | `GET /applications/{id}`, `GET /jobs/{jobId}` |
| Evaluate with AI, Re-run assessment, Try again | `POST /applications/{id}/evaluation` (evaluator then reviewer, in the background; the page refreshes until both finish) |
| Review with AI, Re-run review | `POST /applications/{id}/review` |
| Advance, Reject (with rating and feedback), Change decision | `PUT` / `DELETE /applications/{id}/decision` |
| AI Operations (`/operations`): agent runs and human feedback loop | `GET /agent-executions`, `GET /agent-feedback` |
| Resume download (`/applications/{id}/resume`) | `GET /applications/{id}/resume`, streamed through a portal route handler so the browser never needs Blob Storage access |
| Submit, approve and publish, reject, close, reopen | `PUT /jobs/{id}` with the new status; first publication stamps `publishedAt` |

## Candidate assessment and approval

The candidate page shows the workflow as three steps:

1. **Evaluate**: the `candidate-evaluator` agent (gpt-5.4-mini) scores the resume. Its report shows the initial score, recommendation, strengths, considerations, and a 0–5 score per requirement.
2. **Review**: the `candidate-evaluation-reviewer` agent (gpt-5.4) checks that evaluation and shows the validated score with the change from the initial score, its agreement and confidence, the inconsistencies it found by type and severity, and review comments.
3. **Approve**: the recruiter sees the validated recommendation, rates the AI assessment (**Accurate**, **Partially accurate**, or **Inaccurate**, required when there is an AI recommendation), can write feedback for the agents and a decision comment, and chooses **Advance** or **Reject**. Decisions are disabled while the AI is still running.

The decision records the AI advice it was based on and whether the recruiter followed or overrode it. If the assessment is re-run afterwards, the decision stays and the page warns that it was made on earlier advice. Pages with a step in progress refresh themselves every few seconds. Decisions are recorded as the demo recruiter **Jordan Lee** because the portal has no sign-in yet.

**AI Operations** shows the runs of all three agents with their model, plus the **Human feedback loop**: decisions recorded, how often recruiters followed clear-cut AI recommendations, the rating distribution, how often the reviewer corrected the evaluator, and the latest written feedback with the agent versions it applies to.

On the job form, the recruiter writes informal notes about the role and selects **Generate with AI**. The agent combines them with the role basics and fills the summary, description, responsibilities, and qualifications. Everything stays editable and nothing is saved until the recruiter saves the job; the Foundry response ID is stored as `authoringExecutionId`. **Write it manually instead** shows the empty fields without calling the agent.

Mutations run as Next.js Server Actions (`src/app/jobs/actions.ts`), so the API is only called from the portal server. Job identifiers are generated from the title plus a short random suffix. Validation errors are shown inline and API errors are shown above the form.

## Start locally

Start the FastAPI backend on port 8000, then run:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
npm install
npm run dev -- --port 3001
```

Open [http://localhost:3001](http://localhost:3001). `API_BASE_URL` is server-only and defaults to `http://127.0.0.1:8000` for local development.

Job lists, details, approval views, dashboard summaries, and candidate pages use the backend API. If applications cannot be loaded, the Overview, Jobs list, and job details still render and show the application counts as unavailable; other API failures surface as an error panel rather than falling back to local records.