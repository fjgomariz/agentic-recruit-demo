# Recruiter portal

The recruiter portal retrieves all Jobs from the Recruitment Foundry backend API. Candidate, evaluation, approval, and agent-operation records remain mocked for the current demo phase.

## Start locally

Start the FastAPI backend on port 8000, then run:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
npm install
npm run dev -- --port 3001
```

Open [http://localhost:3001](http://localhost:3001). `API_BASE_URL` is server-only and defaults to `http://127.0.0.1:8000` for local development.

Job lists, details, approval views, dashboard summaries, and candidate-to-Job titles use the backend API. API failures surface as server-rendering errors rather than falling back to local records.