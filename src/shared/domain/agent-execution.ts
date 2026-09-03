/** Runtime lifecycle state of an agent execution. */
export type AgentExecutionStatus = "Queued" | "Running" | "Completed" | "Failed" | "Needs review";

/** Observable record of one Azure AI Foundry agent execution. */
export interface AgentExecution {
  /** Stable execution and trace correlation identifier. */
  id: string;
  /** Human-readable agent name. */
  agentName: string;
  /** Model deployment or model name used by the agent. */
  model: string;
  /** Current execution lifecycle state. */
  status: AgentExecutionStatus;
  /** ISO 8601 execution start timestamp. */
  startedAt: string;
  /** ISO 8601 completion timestamp, when finished. */
  completedAt?: string;
  /** End-to-end execution duration in milliseconds. */
  durationMs?: number;
  /** Estimated model and tool cost in US dollars. */
  estimatedCostUsd?: number;
  /** Prompt/configuration version used for reproducibility. */
  configurationVersion: string;
  /** Related domain entity identifiers, without embedding their content. */
  relatedEntityIds: string[];
  /** Short non-sensitive execution outcome for the demo. */
  outputSummary?: string;
  /** Safe error summary when execution fails. */
  errorMessage?: string;
}
