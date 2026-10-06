# Foundry agents

Each subfolder is one Foundry prompt agent, deployed by `deploy.py` to the project created in `infra/modules/foundry.bicep`.

| Agent | Purpose | Called by | Model |
| --- | --- | --- | --- |
| `job-description-writer` | Drafts a complete job posting (summary, description, responsibilities, qualifications) from role facts and recruiter notes. | `POST /job-description-drafts` | `gpt-5.4-mini` (GlobalStandard) |
| `candidate-evaluator` | Scores a PDF resume against a job posting from 0 to 100, explains strengths, considerations, and per-requirement evidence, and recommends `Strong match`, `Possible match`, `Not a match`, or `Needs manual review`. | Automatically after each application, and `POST /applications/{id}/evaluation` | `gpt-5.4-mini` (GlobalStandard) |

## Agent definition

| File | Content |
| --- | --- |
| `agent.json` | Agent name, description, reasoning effort, and file references. |
| `instructions.md` | System prompt. |
| `output-schema.json` | Strict JSON schema for the response. The API test suite checks each schema matches its API model. |

Agents are immutable and versioned. `deploy.py` hashes the model, instructions, schema, and reasoning settings and stores the hash in the version metadata, so a new version is published only when one of them changes. The API calls each agent by name, which always resolves to the latest version.

## Candidate evaluator

- **Input:** the job posting as text plus the resume attached as a base64 PDF (`input_file`) in the same Responses API call. The model reads the PDF directly; there is no separate text-extraction step.
- **Human in the loop:** the evaluation is advisory. Recruiters record **Advance** or **Reject** separately, and re-running an evaluation never changes the decision.
- **Fairness:** the prompt limits scoring to job-relevant evidence and forbids using or inferring protected characteristics, and raising work authorization, location, or work arrangement unless the resume contradicts an explicit requirement.
- **Prompt injection:** the resume and message are treated as untrusted data. Azure AI Content Safety's prompt shields block resumes that contain instructions aimed at the screening system before they reach the model; the API stores those as **Needs manual review** instead of failing. `samples/resumes/lena-fischer-visual-designer.pdf` demonstrates this.
- **Variance:** scores can differ by a few points between runs of the same resume; recommendations are stable.

## Publish manually

```powershell
pip install -r agents/requirements.txt
$env:AZURE_AI_PROJECT_ENDPOINT = azd env get-value AZURE_AI_PROJECT_ENDPOINT
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = azd env get-value AZURE_AI_MODEL_DEPLOYMENT_NAME
python agents/deploy.py
```

The signed-in identity needs **Foundry User** on the project. CI receives it from Bicep through `AZURE_PRINCIPAL_ID`.

## Runtime and monitoring

The API calls the agents through the Foundry Responses API with its managed identity, which has **Foundry User** on the project. The narrower **Foundry Project Runtime User** role (`responses/*` only) is not enough: invoking an agent by reference also reads the agent definition and fails with `403`.

Every run, successful or not, is recorded in the Cosmos DB `agent-executions` container with the agent version, model, status, duration, token usage, a short non-personal outcome, and the related application and job IDs. The recruiter portal's **AI Operations** page reads these records through `GET /agent-executions`. The Foundry response ID is the record ID, so a run can be found in the traces.

The Application Insights connection on the project enables server-side tracing. Each run appears in the Foundry portal (**Agents → Traces**) and in Application Insights as `invoke_agent <agent>:<version>` with a child `chat gpt-5.4-mini` span, including token usage. The API also emits request, dependency, and log telemetry to the same resource. Client-side message content capture is disabled so resumes are not copied into the API's traces.
