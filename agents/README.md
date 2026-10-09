# Foundry agents

Each subfolder is one Foundry prompt agent, deployed by `deploy.py` to the project created in `infra/modules/foundry.bicep`.

| Agent | Purpose | Called by | Model |
| --- | --- | --- | --- |
| `job-description-writer` | Drafts a complete job posting (summary, description, responsibilities, qualifications) from role facts and recruiter notes. | `POST /job-description-drafts` | `gpt-5.4-mini` (GlobalStandard) |
| `candidate-evaluator` | **Maker.** Scores a PDF resume against a job posting from 0 to 100, explains strengths, considerations, and per-requirement evidence, and recommends `Strong match`, `Possible match`, `Not a match`, or `Needs manual review`. | Automatically after each application, and `POST /applications/{id}/evaluation` | `gpt-5.4-mini` (GlobalStandard) |
| `candidate-evaluation-reviewer` | **Checker.** Re-reads the resume and job, verifies every claim and score in the evaluation, flags unsupported claims, missed evidence, score mismatches, potential bias, and overconfidence, and returns a validated score, agreement, confidence, comments, and the final recommendation. | Automatically after a completed evaluation, and `POST /applications/{id}/review` | `gpt-5.4` (GlobalStandard) |

## Assessment workflow

```text
Application ──► candidate-evaluator (gpt-5.4-mini) ──► candidate-evaluation-reviewer (gpt-5.4) ──► Recruiter approval
                 maker: score + evidence                checker: validated score, findings          decision + rating + feedback
```

1. **Evaluate.** The evaluator scores the resume (about 5–8 seconds).
2. **Review.** When the evaluation completes, the API hands it to the reviewer with the same job, message, and PDF (about 10–20 seconds). A different, larger model reduces correlated mistakes: the checker does not simply agree with the maker. Evaluations routed to manual review (prompt injection or unreadable PDF) skip this step.
3. **Approve.** The recruiter sees both reports and the validated recommendation, rates how accurate the AI assessment was, optionally writes feedback for the agents, and decides **Advance** or **Reject**. The decision stores a snapshot of the AI advice it was based on (recommendation, score, and both run IDs) and whether the recruiter followed or overrode a clear-cut recommendation.

The ratings and feedback form a loop for continuous improvement: `GET /agent-feedback` returns them per decision with the evaluator and reviewer versions, without candidate personal data, and the AI Operations page summarizes them. Use them to tune prompts and to build evaluation datasets for new agent versions.

## Agent definition

| File | Content |
| --- | --- |
| `agent.json` | Agent name, description, reasoning effort, file references, and an optional `modelDeployment` (defaults to `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `gpt-5.4-mini`). The deployment must exist in `agentModelDeployments` in `infra/main.bicep`. |
| `instructions.md` | System prompt. |
| `output-schema.json` | Strict JSON schema for the response. The API test suite checks each schema matches its API model. |

Agents are immutable and versioned. `deploy.py` hashes the model, instructions, schema, and reasoning settings and stores the hash in the version metadata, so a new version is published only when one of them changes. The API calls each agent by name, which always resolves to the latest version.

## Candidate evaluator

- **Input:** the job posting as text plus the resume attached as a base64 PDF (`input_file`) in the same Responses API call. The model reads the PDF directly; there is no separate text-extraction step.
- **Human in the loop:** the evaluation is advisory. Recruiters record **Advance** or **Reject** separately, and re-running an evaluation never changes the decision.
- **Fairness:** the prompt limits scoring to job-relevant evidence and forbids using or inferring protected characteristics, and raising work authorization, location, or work arrangement unless the resume contradicts an explicit requirement.
- **Prompt injection:** the resume and message are treated as untrusted data. Azure AI Content Safety's prompt shields block resumes that contain instructions aimed at the screening system before they reach the model; the API stores those as **Needs manual review** instead of failing. `samples/resumes/lena-fischer-visual-designer.pdf` demonstrates this.
- **Variance:** scores can differ by a few points between runs of the same resume; recommendations are stable.

## Evaluation reviewer

- **Input:** the job posting, the candidate message, the resume PDF, and the evaluator's output in its original JSON shape, marked as untrusted.
- **Rules:** verify, do not trust; keep the original score when it is reasonable; do not invent problems. `agreement` is `Agrees` (same recommendation, score within 5 points), `Partially agrees` (same recommendation, larger change or medium/high findings), or `Disagrees` (different recommendation).
- **Proof that it works:** with a deliberately corrupted evaluation of `tom-becker-junior-frontend-developer.pdf` (score raised to 78, an invented design-system strength, a location remark, and the word "young"), the reviewer returned 10 / `Not a match` / `Disagrees` and flagged the unsupported claim, the score mismatch, the location and age bias, and the overconfidence. On honest evaluations it agrees and reports no issues.
- **Model pinning:** `gpt-5.4` (version `2026-03-05`) is deployed with `NoAutoUpgrade`, so the checker's behavior only changes through a reviewed version bump.

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

The Application Insights connection on the project enables server-side tracing. Each run appears in the Foundry portal (**Agents → Traces**) and in Application Insights as `invoke_agent <agent>:<version>` with a child `chat gpt-5.4-mini` span, including token usage. The API also emits request, dependency, and log telemetry to the same resource. The `azure-ai-projects` client-side instrumentor is intentionally not enabled: in version 2.7.0 it raises `AttributeError` on sampled-out spans and fails the agent call itself. Server-side traces and the `agent-executions` records cover the same runs, and resumes are not copied into the API's own telemetry.

Inputs that Foundry rejects are not retried: a Content Safety block or a PDF the model cannot read (`invalid_file`, for example a damaged or image-only file) is stored as **Needs manual review** with the reason.

## Evaluating the candidate evaluator in Foundry

`evaluations/run_evaluation.py` runs a **Foundry cloud evaluation** against the agent, so the results live in **Foundry → Build → Evaluations** and can be compared run by run.

How it works:

- **One agent, many versions.** The script publishes the lab agent `candidate-evaluator-lab` with the production `candidate-evaluator` definition. A different `--model` or `--instructions` file creates a new version of that same agent; identical settings reuse the existing version. The production agent is never touched.
- **One evaluation, many runs.** The evaluation `candidate-evaluator-quality` holds a fixed [dataset](evaluations/dataset.json) (job, candidate message, resume text and the expected recommendation). Each invocation adds a run, named after the label, model and agent version.
- **Foundry does the work.** For every dataset row Foundry calls the agent version and scores the answer with three criteria: `recommendation_matches` (string check against the expected label), `evidence_based` (model judge: claims supported by the resume) and `ignores_embedded_instructions` (model judge: injected text did not change the outcome). The judge is `EVALUATION_JUDGE_MODEL_DEPLOYMENT` (default `gpt-5.4`).

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e "src/api[dev]" -r agents/requirements.txt -r agents/evaluations/requirements.txt
$env:AZURE_AI_PROJECT_ENDPOINT = azd env get-value AZURE_AI_PROJECT_ENDPOINT
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = azd env get-value AZURE_AI_MODEL_DEPLOYMENT_NAME

.\.venv\Scripts\python agents/evaluations/run_evaluation.py --label baseline
# Another model (any deployment in the Foundry account):
.\.venv\Scripts\python agents/evaluations/run_evaluation.py --label candidate-model --model gpt-5.6-sol
# A prompt variant:
.\.venv\Scripts\python agents/evaluations/run_evaluation.py --label lenient-prompt --instructions agents/evaluations/variants/lenient-prompt.md
```

Open **Evaluations → candidate-evaluator-quality** to see the pass rate per criterion for each run and drill into the answers of any case. Add rows to `dataset.json` to make the evaluation stricter; the string check and the judges stay the same.

Notes:

- The resume is sent as extracted text. The production agent receives a PDF, so this measures the model and the instructions, not PDF handling. The prompt-shield block on `lena-fischer-visual-designer.pdf` is not part of this evaluation.
- With six synthetic cases and a model judge, results are directional. Judges can disagree with a human, and a pass rate on a handful of rows is not a statistical result. A human decides before changing the production agent.
- `infra/main.bicep` declares the `gpt-5.6-sol` deployment in `dev` only, as a candidate model for these runs.