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

## Applying for a job

The apply page (`/jobs/{id}/apply`) asks for a full name, email, an optional short message, and a PDF resume (5 MB max). The form posts to a Server Action, which validates the input and sends a multipart request to `POST /jobs/{id}/applications`. The API stores the resume in Blob Storage and the application in Cosmos DB, and the page shows a confirmation with the application reference. Validation and API errors are shown above the form without clearing the typed values.

`next.config.ts` raises the Server Action body limit to 6 MB so 5 MB resumes fit.
