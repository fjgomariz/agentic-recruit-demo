# Copilot Instructions

General Principles

- Keep the solution simple.
- This is a demo platform.
- Prioritize readability over optimization.
- Use production-like patterns.
- Prefer explicit code over clever code.

Architecture

- Monorepo structure.
- Frontend: Next.js.
- Backend: FastAPI.
- Database: Azure Cosmos DB.
- File Storage: Azure Blob Storage.
- AI: Azure AI Foundry Agent Service.

Folder Structure

src/

  public-portal/
  recruiter-portal/
  api/
  agents/
  evaluations/
  shared/

When creating new code:

- Respect the existing folder structure.
- Avoid creating new top-level folders.
- Reuse existing types.
- Reuse shared models whenever possible.

AI Features

- Design agents to be observable.
- Log inputs and outputs.
- Consider tracing requirements.
- Keep prompts external to business logic.

Code Quality

- Use type annotations.
- Generate documentation comments.
- Create unit tests when applicable.