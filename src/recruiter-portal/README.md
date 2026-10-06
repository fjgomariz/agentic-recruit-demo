# Recruiter portal

The recruiter portal manages Jobs end to end through the Recruitment Foundry backend API, which stores them in Cosmos DB, and shows the applications candidates submit on the careers site. The Candidates section, evaluations, approval-workflow records, and agent operations remain mocked for the current demo phase.

## Job management

| Screen | API call |
| --- | --- |
| Overview, Jobs list, candidate job titles | `GET /jobs` |
| Job details, approval review | `GET /jobs/{id}` |
| Create job (`/jobs/new`) | `POST /jobs` with status `Draft` or `Pending Approval` |
| Edit job (`/jobs/{id}/edit`) | `PUT /jobs/{id}`; lifecycle state is unchanged |
| Generate with AI (create and edit) | `POST /job-description-drafts`, which runs the Foundry `job-description-writer` agent |
| Job details (recent applications), Applications (`/jobs/{id}/applications`) | `GET /jobs/{id}/applications` |
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

Job lists, details, approval views, dashboard summaries, and candidate-to-Job titles use the backend API. API failures surface as an error panel rather than falling back to local records.