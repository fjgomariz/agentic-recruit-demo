import type { AgentExecution, ApprovalWorkflow } from "../domain";
import { createMockAgentExecution, createMockApprovalWorkflow } from "./factories";

/** Canonical mock agent execution telemetry. */
export const mockAgentExecutions: AgentExecution[] = [
  createMockAgentExecution({ id: "run_84f2a", agentName: "Candidate evaluation", model: "gpt-4.1", status: "Completed", startedAt: "2026-09-03T13:24:00Z", completedAt: "2026-09-03T13:24:14.200Z", durationMs: 14_200, estimatedCostUsd: 0.084, configurationVersion: "v2.3", relatedEntityIds: ["application-olivia-bennett"] }),
  createMockAgentExecution({ id: "run_84f29", agentName: "Job authoring", model: "gpt-4.1", status: "Completed", startedAt: "2026-09-03T13:16:00Z", completedAt: "2026-09-03T13:16:09.800Z", durationMs: 9_800, estimatedCostUsd: 0.041, configurationVersion: "v2.3", relatedEntityIds: ["ai-platform-engineer"], outputSummary: "Created a job description for human approval." }),
  createMockAgentExecution({ id: "run_84f21", agentName: "Candidate review", model: "gpt-4.1-mini", status: "Running", startedAt: "2026-09-03T13:12:00Z", durationMs: undefined, estimatedCostUsd: undefined, configurationVersion: "v1.8", relatedEntityIds: ["application-sofia-martin"] }),
];

/** Canonical mock human approval workflows. */
export const mockApprovalWorkflows: ApprovalWorkflow[] = [
  createMockApprovalWorkflow({ id: "approval-ai-platform-engineer", targetType: "Job", targetId: "ai-platform-engineer", status: "Pending", requestedBy: "Daniel Kim", requestedAt: "2026-09-02T10:00:00Z", agentExecutionId: "run_84f29" }),
];
