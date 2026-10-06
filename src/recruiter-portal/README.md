# Recruiter portal

The recruiter portal manages Jobs end to end through the Recruitment Foundry backend API, which stores them in Cosmos DB, and reviews the applications candidates submit on the careers site. Every page reads real data from the API; there is no mock data. Each application is scored by the Foundry `candidate-evaluator` agent, and the recruiter records the decision.

## Screens and API calls

| Screen | API call |
| --- | --- |
| Overview (metrics, open positions, candidates awaiting your decision) | `GET /jobs`, `GET /applications` |
| Jobs list | `GET /jobs`, `GET /applications` (per-job application counts) |
| Job details, approval review | `GET /jobs/{id}` |
| Create job (`/jobs/new`) | `POST /jobs` with status `Draft` or `Pending Approval` |
| Edit job (`/jobs/{id}/edit`) | `PUT /jobs/{id}`; lifecycle state is unchanged |
| Generate with AI (create and edit) | `POST /job-description-drafts`, which runs the Foundry `job-description-writer` agent |
| Job details (recent applications), Applications (`/jobs/{id}/applications`) | `GET /jobs/{id}/applications` |
| Candidates (`/candidates`): best match first, search, job and status filters | `GET /applications`, `GET /jobs` |
| Candidate details (`/candidates/{applicationId}`): AI report, decision | `GET /applications/{id}`, `GET /jobs/{jobId}` |
| Evaluate with AI, Re-evaluate, Try again | `POST /applications/{id}/evaluation` (runs in the background; the page refreshes until it finishes) |
| Advance, Reject, Change decision | `PUT` / `DELETE /applications/{id}/decision` |
| AI Operations (`/operations`) | `GET /agent-executions` |
| Resume download (`/applications/{id}/resume`) | `GET /applications/{id}/resume`, streamed through a portal route handler so the browser never needs Blob Storage access |
| Submit, approve and publish, reject, close, reopen | `PUT /jobs/{id}` with the new status; first publication stamps `publishedAt` |

## Candidate review

Applications are evaluated automatically right after the candidate applies. The candidate page shows the score, recommendation, summary, strengths, considerations, and a 0–5 score per requirement with the evidence, plus the agent version and run ID. Pages showing an evaluation in progress refresh themselves every few seconds.

The AI recommendation is advisory. The recruiter's **Advance** or **Reject** decision, with an optional comment, is stored separately and survives re-evaluation. The dashboard's **Candidates awaiting your decision** lists evaluated candidates without a decision, best match first. Decisions are recorded as the demo recruiter **Jordan Lee** because the portal has no sign-in yet.

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