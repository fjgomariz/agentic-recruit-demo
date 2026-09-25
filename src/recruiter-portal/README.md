# Recruiter portal

The recruiter portal manages Jobs end to end through the Recruitment Foundry backend API, which stores them in Cosmos DB. Candidate, evaluation, approval-workflow, and agent-operation records remain mocked for the current demo phase.

## Job management

| Screen | API call |
| --- | --- |
| Overview, Jobs list, candidate job titles | `GET /jobs` |
| Job details, approval review | `GET /jobs/{id}` |
| Create job (`/jobs/new`) | `POST /jobs` with status `Draft` or `Pending Approval` |
| Edit job (`/jobs/{id}/edit`) | `PUT /jobs/{id}`; lifecycle state is unchanged |
| Submit, approve and publish, reject, close, reopen | `PUT /jobs/{id}` with the new status; first publication stamps `publishedAt` |

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