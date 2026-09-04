# Public candidate portal

The public portal retrieves published Jobs from the Recruitment Foundry backend API. Job data is not stored locally in this application.

## Start locally

Start the FastAPI backend on port 8000, then run:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
npm install
npm run dev -- --port 3000
```

Open [http://localhost:3000](http://localhost:3000). `API_BASE_URL` is server-only and defaults to `http://127.0.0.1:8000` for local development.

Only Jobs with `Published` status are shown. API failures surface as server-rendering errors rather than falling back to local records.
