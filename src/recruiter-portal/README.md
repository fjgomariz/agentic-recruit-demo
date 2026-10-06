# Recruiter portal

The recruiter portal manages Jobs end to end through the Recruitment Foundry backend API, which stores them in Cosmos DB, and reviews the applications candidates submit on the careers site. Every application, candidate, and count on the Overview, Jobs, and Candidates pages comes from the API. Only the AI Operations page and the approval history on the job approval page still use mock data. Candidates show **Pending evaluation** until AI evaluation is added in a later phase.

## Screens and API calls

| Screen | API call |
| --- | --- |
| Overview (metrics, open positions, candidates awaiting review) | `GET /jobs`, `GET /applications` |
| Jobs list | `GET /jobs`, `GET /applications` (per-job application counts) |
| Job details, approval review | `GET /jobs/{id}` |
| Create job (`/jobs/new`) | `POST /jobs` with status `Draft` or `Pending Approval` |
| Edit job (`/jobs/{id}/edit`) | `PUT /jobs/{id}`; lifecycle state is unchanged |
| Generate with AI (create and edit) | `POST /job-description-drafts`, which runs the Foundry `job-description-writer` agent |
| Job details (recent applications), Applications (`/jobs/{id}/applications`) | `GET /jobs/{id}/applications` |
| Candidates (`/candidates`) with search by name or email and a job filter | `GET /applications`, `GET /jobs` |
| Candidate details (`/candidates/{applicationId}`) | `GET /applications/{id}`, `GET /jobs/{jobId}` |
| Resume download (`/applications/{id}/resume`) | `GET /applications/{id}/resume`, streamed through a portal route handler so the browser never needs Blob Storage access |
| Submit, approve and publish, reject, close, reopen | `PUT /jobs/{id}` with the new status; first publication stamps `publishedAt` |

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