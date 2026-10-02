# Foundry agents

Each subfolder is one Foundry prompt agent, deployed by `deploy.py` to the project created in `infra/modules/foundry.bicep`.

| Agent | Purpose | Model |
| --- | --- | --- |
| `job-description-writer` | Drafts a complete job posting (summary, description, responsibilities, qualifications) from role facts and recruiter notes. | `gpt-5.4-mini` (GlobalStandard) |

## Agent definition

| File | Content |
| --- | --- |
| `agent.json` | Agent name, description, reasoning effort, and file references. |
| `instructions.md` | System prompt. |
| `output-schema.json` | Strict JSON schema for the response. The API test suite checks it matches `JobDescriptionDraft`. |

Agents are immutable and versioned. `deploy.py` hashes the model, instructions, schema, and reasoning settings and stores the hash in the version metadata, so a new version is published only when one of them changes. The API calls the agent by name, which always resolves to the latest version.

## Publish manually

```powershell
pip install -r agents/requirements.txt
$env:AZURE_AI_PROJECT_ENDPOINT = azd env get-value AZURE_AI_PROJECT_ENDPOINT
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = azd env get-value AZURE_AI_MODEL_DEPLOYMENT_NAME
python agents/deploy.py
```

The signed-in identity needs **Foundry User** on the project. CI receives it from Bicep through `AZURE_PRINCIPAL_ID`.

## Runtime and monitoring

The API (`POST /job-description-drafts`) calls the agent through the Foundry Responses API with its managed identity, which has **Foundry User** on the project. The narrower **Foundry Project Runtime User** role (`responses/*` only) is not enough: invoking an agent by reference also reads the agent definition and fails with `403`. The response ID is returned to the recruiter portal and stored on the job as `authoringExecutionId`.

The Application Insights connection on the project enables server-side tracing. Each run appears in the Foundry portal (**Agents → Traces**) and in Application Insights as `invoke_agent job-description-writer:<version>` with a child `chat gpt-5.4-mini` span, including token usage. The API also emits its own request, dependency, and log telemetry to the same Application Insights resource.
