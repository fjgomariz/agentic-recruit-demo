import type { AgentExecution, ApprovalWorkflow } from "../domain";

/** Creates a complete mock approval workflow with optional field overrides. */
export function createMockApprovalWorkflow(overrides: Partial<ApprovalWorkflow> = {}): ApprovalWorkflow {
  return {
    id: "approval-sample-job",
    targetType: "Job",
    targetId: "sample-job",
    status: "Pending",
    requestedBy: "Jordan Lee",
    requestedAt: "2026-09-02T10:00:00Z",
    ...overrides,
  };
}

/** Creates a complete mock agent execution with optional field overrides. */
export function createMockAgentExecution(overrides: Partial<AgentExecution> = {}): AgentExecution {
  return {
    id: "run-sample-evaluation",
    agentName: "Candidate evaluation",
    model: "gpt-4.1",
    status: "Completed",
    startedAt: "2026-09-02T09:00:10Z",
    completedAt: "2026-09-02T09:00:24Z",
    durationMs: 14_200,
    estimatedCostUsd: 0.084,
    configurationVersion: "v2.3",
    relatedEntityIds: ["application-sample-candidate"],
    ...overrides,
  };
}
